"""Independent arithmetic/token model including completion/consume collisions."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
TB=r'''`timescale 1ns/1ps
module tail_tb;
 reg clk=0;always #5 clk=~clk;reg rst_n=0,clear=0,accept=0,in_lane=0,consume=0;reg[2:0] in_tag=0,query_tag=0;reg[1:0] operation=0;reg[31:0] a=0,b=0;
 wire query_ready,forward_valid,forward_lane,busy;wire[31:0] query_data,forward_data;wire[2:0] forward_tag;wire[3:0] next_forward_tag;
 nc_mul_pipeline dut(.clk(clk),.rst_n(rst_n),.clear(clear),.accept(accept),.in_lane(in_lane),.in_tag(in_tag),.operation(operation),.a(a),.b(b),.query_tag(query_tag),.consume(consume),.query_ready(query_ready),.query_data(query_data),.forward_valid(forward_valid),.forward_lane(forward_lane),.forward_tag(forward_tag),.forward_data(forward_data),.busy(busy),.next_forward_tag(next_forward_tag));
 localparam EARLY_LOW=@LOW@,EARLY_HIGH=@HIGH@;
 reg[7:0] active=0;integer due[0:7],ready_at[0:7];reg[31:0] value[0:7];reg lane[0:7];reg[1:0] op[0:7];
 reg[31:0] rng=1;integer seed=1,cyc,i,idx,chosen,found,lo_idx,hi_idx,expect_idx,accepts=0,consumes=0,flushes=0,collisions=0,early=0;integer ops[0:3];reg expected_ready;
 task randomize;begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);end endtask
 function[31:0] model_product;input[31:0] x,y;input[1:0] f;reg signed[32:0] sx,sy;reg signed[65:0] p;begin sx={(f==1 || f==2) && x[31],x};sy={f==1 && y[31],y};p=sx*sy;model_product=f==0 ? p[31:0] : p[63:32];end endfunction
 initial begin
  if($value$plusargs("seed=%d",seed)) begin end rng=seed;for(i=0;i<4;i=i+1)ops[i]=0;
  repeat(2) @(negedge clk);rst_n=1;
  for(cyc=0;cyc<30000;cyc=cyc+1) begin
   randomize;clear=cyc>8 && cyc<29936 && rng[10:5]==0;query_tag=cyc<4 ? 0 : cyc<6 ? 1 : rng[2:0];
   if(cyc>=29936) query_tag=cyc%8;
   found=0;chosen=0;for(i=0;i<8;i=i+1)begin idx=(rng[5:3]+i)%8;if(!active[idx] && !found)begin chosen=idx;found=1;end end
   accept=cyc<2 ? 1 : cyc<6 || cyc>=29936 ? 0 : found && rng[12:11]!=0;
   in_tag=cyc<2 ? cyc : chosen;operation=cyc==0 ? 1 : cyc==1 ? 0 : rng[14:13];in_lane=rng[15];
   randomize;a=rng;randomize;b=rng;
   case(cyc%16)0:a=0;1:a=32'hffffffff;2:a=32'h80000000;3:a=32'h7fffffff;4:b=32'hffffffff;5:b=32'h80000000;6:b=0;default:;endcase
   #1;expected_ready=active[query_tag] && cyc>=ready_at[query_tag];consume=!clear && expected_ready && (cyc<6 || cyc>=29936 || rng[18:17]!=0);
   #1;if(!clear)begin
    if(query_ready!==expected_ready) $fatal(1,"Ready/token model seed=%0d cycle=%0d q=%0d actual=%0d expected=%0d active=%h",seed,cyc,query_tag,query_ready,expected_ready,active);
    if(expected_ready && query_data!==value[query_tag]) $fatal(1,"Arithmetic/query identity seed=%0d cycle=%0d q=%0d actual=%h expected=%h",seed,cyc,query_tag,query_data,value[query_tag]);
   end
   lo_idx=-1;hi_idx=-1;for(i=0;i<8;i=i+1)if(active[i] && due[i]==cyc)begin if(op[i]==0)lo_idx=i;else hi_idx=i;end
   expect_idx=lo_idx>=0 ? lo_idx : hi_idx;
   if(!clear && lo_idx>=0 && hi_idx>=0)collisions=collisions+1;
   if(consume)begin consumes=consumes+1;if(due[query_tag]==cyc)early=early+1;end
   @(posedge clk);#1;
   if(clear)begin if(active!=0)flushes=flushes+1;active=0;if(forward_valid) $fatal(1,"Clear left broadcast");end
   else begin
    if(forward_valid!==(expect_idx>=0)) $fatal(1,"Broadcast valid cycle=%0d",cyc);
    if(expect_idx>=0 && (forward_data!==value[expect_idx] || forward_tag!==expect_idx[2:0] || forward_lane!==lane[expect_idx])) $fatal(1,"Broadcast arithmetic/identity cycle=%0d",cyc);
    if(consume)active[query_tag]=0;
    if(accept)begin
     if(active[in_tag]) $fatal(1,"Test reused live tag");active[in_tag]=1;value[in_tag]=model_product(a,b,operation);op[in_tag]=operation;lane[in_tag]=in_lane;due[in_tag]=cyc+(operation==0 ? 2 : 3);ready_at[in_tag]=due[in_tag]+((operation==0 ? EARLY_LOW : EARLY_HIGH) ? 0 : 1);accepts=accepts+1;ops[operation]=ops[operation]+1;
    end
   end
   @(negedge clk);
  end
  if(active!=0 || busy) $fatal(1,"Did not drain");
  if(accepts<5000 || consumes<1000 || flushes<50 || collisions<20 || (EARLY_LOW && early<100)) $fatal(1,"Coverage too small");
  for(i=0;i<4;i=i+1)if(ops[i]<500)$fatal(1,"Missing op");
  $display("PASS terminal MUL model seed=%0d cycles=30000 accepts=%0d consumes=%0d flushes=%0d collisions=%0d early=%0d ops=%0d,%0d,%0d,%0d",seed,accepts,consumes,flushes,collisions,early,ops[0],ops[1],ops[2],ops[3]);$finish;
 end
endmodule
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);out=src/'mul_unit';out.mkdir(exist_ok=True);tb=out/'tail_tb.v';low=not a.variant.endswith('mulprobe');high=a.variant.endswith('multail');tb.write_text(TB.replace('@LOW@',str(int(low))).replace('@HIGH@',str(int(high))));iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe');inputs=[Path(__file__).resolve(),src/'nc_mul_pipeline.v',tb];tests=[]
 def run(cmd,log):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(out/log).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(p.stdout+p.stderr)[-2200:];return p.stdout.decode(errors='replace')
 run([iv,'-g2012','-s','tail_tb','-o',out/'unit.vvp',src/'nc_mul_pipeline.v',tb],'compile.log')
 for seed in (17,91,2026):
  t=run([vvp,out/'unit.vvp',f'+seed={seed}'],str(seed)+'.log');assert 'PASS terminal MUL model' in t;tests.append(t.strip())
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,cycles=90000,scope='Independent direct signed/unsigned product, all4ops, random query/consume/backpressure/clear/token reuse, low/high simultaneous completion and unchanged registered broadcast priority',input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print(a.variant,'independent MUL model PASS 90000 cycles')
if __name__=='__main__':main()
