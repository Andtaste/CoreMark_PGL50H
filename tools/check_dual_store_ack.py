"""Directed detached-response tests and actual-SoC local-store contract checks."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',default='dual_boundary_storeack');ap.add_argument('--mode',choices=('module','soc','uart'),required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant)
 if a.mode=='uart':
  base=ROOT/'tools/check_dual_timing80_uart.py';s=base.read_text().replace("'simulation/results/load_bp_dual_boundary_pair'",repr('simulation/results/load_bp_'+a.variant));ns={'__file__':str(base),'__name__':'store_ack_uart'};exec(compile(s,str(base),'exec'),ns);ns['main']();p=src/'uart80/result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__));save(p,x);return
 out=src/('posted_'+a.mode);out.mkdir(exist_ok=True);inputs=[Path(__file__).resolve()];tests=[]
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
 def run(cmd,name):
  x=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(out/name).write_bytes(x.stdout+x.stderr);assert x.returncode==0,(x.stdout+x.stderr)[-2800:];return x.stdout.decode(errors='replace')
 if a.mode=='module':
  tb=out/'posted_tb.v';tb.write_text('''`timescale 1ns/1ps
module posted_tb;
 reg clk=0;always #5 clk=~clk;reg rst_n=0,kill=0,valid=0,req_ready=0,rsp_valid=0,rsp_error=0,mul_ready=1;
 reg[279:0] packet=0;reg[31:0] rsp_data=0;wire ready,wb_valid,req_valid,req_write,rsp_ready;wire[279:0] wb_packet;wire[31:0] req_addr,req_data;wire[3:0] req_mask;reg[68:0] saved;
 nc_memory #(.EARLY_REQUEST(1),.POST_LOCAL_STORES(1)) m(.clk(clk),.rst_n(rst_n),.kill(kill),.valid(valid),.ready(ready),.packet(packet),.launch_address(packet[148:117]),.write_address(),.side_packet(65'b0),.wb_valid(wb_valid),.wb_packet(wb_packet),.wb_side(),.mul_tag(),.mul_ready(mul_ready),.mul_data(32'habc),.mul_consume(),.req_valid(req_valid),.req_ready(req_ready),.req_addr(req_addr),.req_data(req_data),.req_mask(req_mask),.req_write(req_write),.rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_data(rsp_data),.rsp_error(rsp_error));
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task reset;begin rst_n=0;kill=0;valid=0;req_ready=0;rsp_valid=0;rsp_error=0;mul_ready=1;tick;rst_n=1;end endtask
 task offer;input[3:0] kind;input[31:0] addr;input[2:0] f3,tag;input fault;begin
 packet=0;packet[279:277]=tag;packet[276:245]=32'h100+{27'b0,tag,2'b0};packet[148:117]=addr;packet[116:85]=32'hfedcba98;packet[180:149]=32'h789;packet[10:8]=f3;packet[7:4]=kind;packet[3]=kind==4;packet[15:11]=10;packet[2]=fault;valid=1;#1;end endtask
 initial begin
 reset;offer(5,32'h10000000,2,0,0);req_ready=1;#1;if(req_valid) $fatal(1,"Store escaped register boundary");tick;valid=0;req_ready=0;#1;saved={req_write,req_mask,req_data,req_addr};
 repeat(4) begin if(!req_valid || wb_valid || {req_write,req_mask,req_data,req_addr}!==saved) $fatal(1,"Blocked store payload/completion");tick;end
 req_ready=1;offer(0,0,0,1,0);if(!ready || !wb_valid || wb_packet[279:277]!=0 || !m.posted_fire) $fatal(1,"Accepted local store did not fast-complete");tick;valid=0;
 if(!m.posted_response || !wb_valid || wb_packet[279:277]!=1) $fatal(1,"ALU turnover identity");tick;
 repeat(3) begin if(wb_valid || !rsp_ready) $fatal(1,"Detached response produced extra WB");tick;end
 rsp_valid=1;rsp_data=32'hdeadbeef;#1;if(wb_valid || m.response) $fatal(1,"Posted ack treated as instruction response");tick;rsp_valid=0;if(m.posted_response) $fatal;
 $display("PASS registered store payload/backpressure, early completion, ALU turnover and delayed detached ack");
 reset;req_ready=1;offer(5,32'h10000000,2,0,0);tick;offer(4,32'h10000004,2,2,0);
 if(!ready || !wb_valid || m.early_request || req_addr!=32'h10000000) $fatal(1,"Younger load borrowed older store request");tick;valid=0;
 repeat(3) begin if(req_valid || wb_valid) $fatal(1,"No credit while detached response absent");tick;end
 rsp_valid=1;rsp_data=32'hbadbad00;#1;if(!req_valid || req_write || req_addr!=32'h10000004 || wb_valid || m.response) $fatal(1,"Posted ack/load request ownership");tick;rsp_valid=0;
 if(!m.sent || m.posted_response) $fatal(1,"Load acceptance tag state");rsp_valid=1;rsp_data=32'h12345678;#1;
 if(!wb_valid || wb_packet[279:277]!=2 || wb_packet[180:149]!=32'h12345678 || wb_packet[2]) $fatal(1,"Load consumed posted ack data");tick;rsp_valid=0;
 $display("PASS store-to-load handoff, detached credit, late response and load data isolation");
 reset;req_ready=1;offer(5,32'h10000000,2,0,0);tick;offer(5,32'h10000004,2,1,0);if(!wb_valid || wb_packet[279:277]!=0) $fatal;tick;
 rsp_valid=1;offer(5,32'h10000008,2,2,0);if(!wb_valid || wb_packet[279:277]!=1 || !m.posted_fire) $fatal;tick;valid=0;
 if(!wb_valid || wb_packet[279:277]!=2 || !m.posted_fire) $fatal;tick;if(wb_valid) $fatal(1,"Duplicate store completion");tick;rsp_valid=0;
 if(m.posted_response) $fatal(1,"Consecutive posted response not drained");
 $display("PASS consecutive one-per-cycle stores with response replacement");
 reset;req_ready=1;offer(5,32'h10000000,2,0,0);tick;valid=0;tick;kill=1;
 repeat(2) begin if(req_valid || wb_valid || !rsp_ready || !m.posted_response) $fatal(1,"Kill lost accepted-store response ownership");tick;end
 rsp_valid=1;tick;rsp_valid=0;kill=0;if(m.posted_response || m.slot_valid) $fatal;
 $display("PASS accepted local-store response drains across younger kill");
 reset;req_ready=1;offer(5,32'h20000008,2,4,0);tick;valid=0;
 if(!req_valid || !req_write || wb_valid || m.posted_fire) $fatal(1,"MMIO incorrectly posted");tick;rsp_valid=1;rsp_error=1;offer(4,32'h10000000,2,5,0);
 if(!wb_valid || !wb_packet[2] || wb_packet[20:16]!=7 || ready || req_valid) $fatal(1,"MMIO late error allowed younger read");tick;kill=1;tick;
 $display("PASS MMIO/nonlocal normal response/error contract and precise younger-side-effect block");
 reset;req_ready=1;offer(5,32'h10000000,2,1,1);tick;valid=0;
 if(req_valid || !wb_valid || !wb_packet[2] || m.posted_fire) $fatal(1,"Faulting store published");tick;kill=1;tick;
 $display("PASS faulting local store never writes or fast-completes cleanly");
 reset;req_ready=1;offer(5,32'h10000002,0,0,0);tick;valid=0;if(req_mask!=4'b0100 || req_data!=32'hba980000 || !wb_valid) $fatal(1,"Byte mask/shift");tick;rsp_valid=1;tick;rsp_valid=0;
 offer(5,32'h10000002,1,1,0);tick;valid=0;if(req_mask!=4'b1100 || req_data!=32'hba980000 || !wb_valid) $fatal(1,"Half mask/shift");tick;rsp_valid=1;tick;rsp_valid=0;
 $display("PASS byte/half store masks and shifted data stay registered");
 reset;req_ready=1;mul_ready=0;offer(6,0,0,2,0);tick;offer(5,32'h10000000,2,3,0);
 repeat(3) begin if(ready || wb_valid || req_valid) $fatal(1,"Store passed older incomplete MUL");tick;end
 mul_ready=1;#1;if(!ready || !wb_valid || req_valid) $fatal;tick;valid=0;if(!m.posted_fire || wb_packet[279:277]!=3) $fatal;tick;rsp_valid=1;tick;
 $display("PASS younger store cannot bypass incomplete older multiply");$finish;
 end
 initial begin #20000;$fatal(1,"timeout");end
endmodule
''');inputs +=[tb,src/'nc_memory.v'];run([iv,'-g2012','-s','posted_tb','-o',out/'sim.vvp',src/'nc_memory.v',tb],'compile.log');s=run([vvp,out/'sim.vvp'],'run.log');tests=[line for line in s.splitlines() if line.startswith('PASS ')];assert len(tests)==8,s
 else:
  original=src/'checks/soc_tb.v';tb=out/'soc_tb.v';monitor='''
 integer posted_count=0,drain_count=0,local_count=0;
 reg was_local;
 always @(posedge clk) if(rst_n) begin
  was_local=dut.bus.da_fire && dut.bus.dwrite && (dut.bus.db0 || dut.bus.db1);
  if(dut.cpu.memory.posted_fire) begin
   posted_count=posted_count+1;
   if(!was_local || !dut.cpu.d_req_valid || !dut.cpu.d_req_ready || dut.cpu.memory.exception || !dut.cpu.memory.wb_valid) $fatal(1,"Posted completion lacks accepted clean local store");
   if(dut.cpu.memory.early_request) $fatal(1,"Double use of posted store request");
  end
  if(dut.cpu.memory.posted_response && dut.cpu.d_rsp_valid) begin
   drain_count=drain_count+1;if(!dut.cpu.d_rsp_ready || dut.cpu.memory.response || dut.cpu.d_error) $fatal(1,"Detached local response ownership/guarantee");
  end
  #1;
  if(was_local) begin local_count=local_count+1;if(!dut.cpu.d_rsp_valid || dut.cpu.d_error) $fatal(1,"Real local bus violates no-late-error contract");end
 end
 always @(negedge clk) if(finish_count==1) begin
  if(posted_count==0 || posted_count!=drain_count || local_count!=posted_count) $fatal(1,"Posted request/completion/drain accounting");
  $display("POSTED_CONTRACT posted=%0d drained=%0d local=%0d",posted_count,drain_count,local_count);
 end
''';tb.write_text(original.read_text().replace('endmodule',monitor+'\nendmodule'));g=json.loads((src/'generation.json').read_text());files=[]
  for d in ('core','perips','sys_bus','top'):
   for p in sorted((ROOT/'hardware/pds/source'/d).glob('*.v')):files.append(src/p.name if str(p.relative_to(ROOT)) in g['override_sha256'] else p)
  files +=[src/'pango_ram_wide_models.v'];inputs +=[original,tb,*files];run([iv,'-g2012','-s','soc_tb','-o',out/'sim.vvp',*files,tb],'compile.log')
  for name in ('random_17','random_91','random_2026','directed','soc_faults'):
   image=ROOT/('simulation/results/'+name+'.hex');inputs.append(image);s=run([vvp,out/'sim.vvp',f'+image={image}',f'+trace={out}/{name}.trace',f'+uart={out}/unused.txt'],name+'.log');assert 'PASS cycles=' in s and 'POSTED_CONTRACT' in s,s[-2000:];tests.append(name+' '+next(line for line in s.splitlines() if line.startswith('POSTED_CONTRACT')))
 save(out/'result.json',dict(status='PASS',variant=a.variant,tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}));print(a.mode,'posted contract PASS',len(tests))
if __name__=='__main__':main()
