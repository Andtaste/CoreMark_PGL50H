"""Random fetch protocol equivalence and cached-pair conflict invariant."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
trial=ROOT/'simulation/results/autonomous_20261022/fetch_pair_conflict'
parent=ROOT/json.loads((trial/'parent_baseline.json').read_text())['project_directory']/'source/core/nc_fetch.v'
actual=trial/'source/core/nc_fetch.v'
out=trial/'fetch_unit';out.mkdir(exist_ok=True)
gold=out/'gold_fetch.v';gold.write_text(parent.read_text().replace('module nc_fetch','module gold_fetch',1))
bench=out/'fetch_tb.v'
ports='''.clk(clk),.rst_n(rst_n),.redirect(redirect),.stop(stop),.target(target),
 .bp_flush(1'b0),.bp_update_valid(1'b0),.bp_update_branch(1'b0),.bp_update_conditional(1'b0),
 .bp_update_taken(1'b0),.bp_update_pc(32'b0),.bp_update_target(32'b0),
 .prediction(pred[N]),.prediction1(pred1[N]),.req_valid(qv[N]),.req_ready(qready),.req_addr(qa[N]),
 .rsp_valid(rv),.rsp_ready(rr[N]),.rsp_data(data),.rsp_error(error),.pair_flags(flags[N]),
 .primary_multiply_hint(mul[N]),.valid(valid[N]),.ready(ready),.take_two(take_two),.second_valid(second[N]),
 .pc(pc[N]),.inst(inst[N]),.inst1(inst1[N]),.fault(fault[N])'''
s='''`timescale 1ns/1ps
module fetch_tb;
 reg clk=0;always #5 clk=!clk;
 reg rst_n=0,redirect=0,stop=0,ready=0,take_two=0,qready=0,rv=0,error=0;
 reg[31:0] target=0;reg[63:0] data=0;
 wire[1:0] qv,rr,valid,second,mul,fault;
 wire[31:0] qa[0:1],pc[0:1],inst[0:1],inst1[0:1],pred[0:1],pred1[0:1];
 wire[9:0] flags[0:1];wire conflict;
'''
s+=' gold_fetch #(.ENABLE_BP(0)) reference('+ports.replace('N','0')+');\n'
s+=' nc_fetch #(.ENABLE_BP(0)) dut('+ports.replace('N','1')+',.pair_conflict(conflict));\n'
s+='''
 reg pending=0;integer delay_left=0;reg[31:0] address=0,rng=1;
 integer cycle=0,seed=0,pop1=0,pop2=0,cross_count=0,redirects=0,stale=0,pairs=0,conflicts=0;
 function[31:0] step(input[31:0] x);step=x*32'd1664525+32'd1013904223;endfunction
 function[31:0] instruction(input[31:0] x);
  instruction={7'b0,x[4:0],x[9:5],3'b0,x[14:10],7'h33};
 endfunction
 wire expected=inst[1][11:7]!=0 &&
  (inst[1][11:7]==inst1[1][19:15] || inst[1][11:7]==inst1[1][24:20] || inst[1][11:7]==inst1[1][11:7]);
 initial if($value$plusargs("seed=%d",seed)) rng=seed;
 always @(negedge clk) begin
  rst_n=cycle>=3;rng=step(rng);ready=rng[31:28]<12;take_two=rng[27];qready=rng[26:23]<12;
  stop=rng[22:19]==0;redirect=rng[18:13]==0;target={rng[29:0],2'b0};
  if(cycle%800<100) begin ready=0;stop=0;redirect=0;qready=1;end
  if(cycle%800>=100 && cycle%800<180) begin ready=1;stop=0;redirect=0;qready=1;end
  if(cycle%800==80) redirect=1;
  if(cycle%800==300) begin qready=0;redirect=1;end
  rv=pending && delay_left==0;
  data={instruction(address^32'h36c950e7),instruction(address^32'h618bad23)};
  error=address[9:5]==5'b10101;
 end
 always @(posedge clk) begin
  cycle<=cycle+1;
  if(!rst_n) begin pending<=0;delay_left<=0;end
  else begin
   if({qv[0],rr[0],valid[0],second[0]} !== {qv[1],rr[1],valid[1],second[1]}) $fatal(1,"Fetch handshake mismatch");
   if(qv[0] && qa[0]!==qa[1]) $fatal(1,"Request mismatch");
   if(valid[0] && {pc[0],inst[0],fault[0],pred[0],mul[0]} !== {pc[1],inst[1],fault[1],pred[1],mul[1]}) $fatal(1,"Primary head mismatch");
   if(second[0]) begin
    if({inst1[0],pred1[0],flags[0]} !== {inst1[1],pred1[1],flags[1]}) $fatal(1,"Secondary head mismatch");
    if(conflict !== expected) $fatal(1,"Stale cached conflict cycle=%0d",cycle);
    pairs<=pairs+1;if(conflict) conflicts<=conflicts+1;
   end
   if(pending && delay_left>0) delay_left<=delay_left-1;
   if(rv && rr[0]) pending<=0;
   if(qv[0] && qready) begin
    if(pending && !(rv && rr[0])) $fatal(1,"Multiple outstanding requests");
    pending<=1;address<=qa[0];delay_left<=cycle%800<180 ? 0 : {29'b0,rng[12:10]};
   end
   if(valid[0] && ready) begin
    if(second[0] && take_two) pop2<=pop2+1;else pop1<=pop1+1;
    if(reference.rd[0]) cross_count<=cross_count+1;
   end
   if(redirect) redirects<=redirects+1;
   if(rv && reference.flight_stale) stale<=stale+1;
   if(cycle==100003) begin
    if(pop1==0 || pop2==0 || cross_count==0 || redirects==0 || stale==0 || pairs==0 || conflicts==0) $fatal(1,"Coverage missing");
    $display("PASS fetch cycles=100000 pop1=%0d pop2=%0d cross_count=%0d redirects=%0d stale=%0d pairs=%0d conflicts=%0d",pop1,pop2,cross_count,redirects,stale,pairs,conflicts);$finish;
   end
  end
 end
endmodule
'''
bench.write_text(s)
iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
r=subprocess.run([str(iv),'-g2012','-s','fetch_tb','-o',str(out/'sim.vvp'),str(gold),str(actual),str(bench)],capture_output=True,timeout=90)
(out/'compile.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stderr
tests=[]
for seed in [17,91,2026]:
 r=subprocess.run([str(vvp),str(out/'sim.vvp'),f'+seed={seed}'],capture_output=True,timeout=180)
 (out/f'seed_{seed}.log').write_bytes(r.stdout+r.stderr)
 assert r.returncode==0 and b'PASS fetch cycles=100000' in r.stdout,r.stdout+r.stderr
 tests.append(r.stdout.decode().strip());print(tests[-1],flush=True)
(out/'result.json').write_text(json.dumps(dict(status='PASS',cycles=300000,tests=tests,scope='Random 64-bit fetch response delays, stop, one/two pops, head parity crossing, fault and stale redirects; BP disabled here and exercised by full-core tests; canonical ADD fields provide independent conflict oracle.',input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [parent,actual,gold,bench,Path(__file__)]}),indent=2)+'\n')
