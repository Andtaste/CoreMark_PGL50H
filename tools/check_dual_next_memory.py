"""Exercise one-shot memory responses while a same-group result is outstanding."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
TB=r'''`timescale 1ns/1ps
module next_memory_tb;
 parameter POSTED=1;
 reg clk=0;always #5 clk=~clk;reg rst_n=0,kill=0,valid=0,req_ready=0,rsp_valid=0,rsp_error=0,mul_ready=0;
 reg[279:0] packet=0;reg[64:0] side_packet=0;reg[31:0] rsp_data=0;
 reg pending_valid=0,pending_done=0;reg[2:0] pending_tag=0;reg[64:0] pending_side=0;
 wire ready,wb_valid,req_valid,req_write,rsp_ready,mul_consume;wire[279:0] wb_packet;wire[64:0] wb_side;wire[31:0] req_addr,req_data;wire[3:0] req_mask;
 nc_memory #(.EARLY_REQUEST(1),.POST_LOCAL_STORES(POSTED)) m(.clk(clk),.rst_n(rst_n),.kill(kill),.valid(valid),.ready(ready),.packet(packet),.side_packet(side_packet),.wb_side(wb_side),
  PENDING_PORTS
  .launch_address(packet[148:117]),.write_address(),.wb_valid(wb_valid),.wb_packet(wb_packet),.mul_tag(),.mul_ready(mul_ready),.mul_data(32'h1234abcd),.mul_consume(mul_consume),
  .req_valid(req_valid),.req_ready(req_ready),.req_addr(req_addr),.req_data(req_data),.req_mask(req_mask),.req_write(req_write),.rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_data(rsp_data),.rsp_error(rsp_error));
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task reset;begin rst_n=0;kill=0;valid=0;req_ready=0;rsp_valid=0;rsp_error=0;mul_ready=0;pending_valid=0;pending_done=0;tick;rst_n=1;end endtask
 task offer;input[3:0] k;input[2:0] tag;input secondary;begin
 packet=0;packet[279:277]=tag;packet[276:245]=32'h100;packet[244:213]=k==4 ? 32'h00002503 : 32'h00a02023;
 packet[148:117]=32'h10000000;packet[116:85]=32'habcd1234;packet[15:11]=10;packet[10:8]=2;packet[7:4]=k;packet[3]=k==4;
 side_packet=secondary ? {1'b1,32'h020001b3,32'b0} : 65'b0;valid=1;#1;
 end endtask
 integer n,delay;reg[31:0] expected;integer completed=0,accepted=0;
 initial begin
  for(n=0;n<128;n=n+1) begin
   reset;expected=32'h87654321^(n*32'h1020304);delay=(n%7)+1;
   offer(4,n[2:0],WITH_MUL);SET_PENDING
   req_ready=1;#1;if(!req_valid || req_write) $fatal(1,"early load request");tick;valid=0;
   rsp_valid=1;rsp_data=expected;rsp_error=n%11==0;#1;
   if(wb_valid || !rsp_ready) $fatal(1,"group completed before younger result");tick;rsp_valid=0;rsp_error=0;rsp_data=~expected;
   repeat(delay) begin #1;if(wb_valid || req_valid || rsp_ready) $fatal(1,"response lost/replayed or early group completion");tick;end
   FINISH_PENDING
   #1;if(!wb_valid || wb_packet[180:149]!==expected || wb_packet[2]!== (n%11==0) || wb_side!==EXPECTED_SIDE) $fatal(1,"saved response/result/error/side identity");
   if(wb_packet[2] && wb_packet[20:16]!=5) $fatal(1,"load fault cause");tick;
   repeat(2) begin if(wb_valid || req_valid || mul_consume) $fatal(1,"duplicate group completion");tick;end
   completed=completed+1;
  end
  STORE_CASES
  reset;offer(4,3,WITH_MUL);SET_PENDING
  req_ready=1;tick;valid=0;rsp_valid=1;rsp_data=32'hdeadbeef;tick;rsp_valid=0;kill=1;tick;kill=0;
  FINISH_PENDING
  repeat(3) begin if(wb_valid || req_valid || mul_consume) $fatal(1,"killed delayed result escaped");tick;end
  $display("PASS retained one-shot load data/error, atomic side identity, randomized delay/token reuse, kill POSTED=%0d groups=%0d stores=%0d",POSTED,completed,accepted);$finish;
 end
 initial begin #500000;$fatal(1,"timeout");end
endmodule
'''
STORE=r'''
 for(n=0;n<32;n=n+1) begin
  reset;offer(5,n[2:0],1);req_ready=1;tick;valid=0;#1;
  if(!req_valid || !req_write || wb_valid) $fatal(1,"paired store acceptance");
  tick;accepted=accepted+1;rsp_valid=1;#1;
  if(wb_valid) $fatal(1,"store group retired before MUL");tick;rsp_valid=0;
  repeat(n%5+1) begin if(req_valid || wb_valid) $fatal(1,"accepted store replay/lost completion");tick;end
  mul_ready=1;#1;if(!wb_valid || !mul_consume || wb_side!={1'b1,32'h020001b3,32'h1234abcd}) $fatal(1,"store/MUL completion");tick;
  repeat(2) begin if(wb_valid || req_valid || mul_consume) $fatal(1,"duplicate store/MUL");tick;end
 end
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);out=src/'next_memory_checks';out.mkdir(exist_ok=True);split=a.variant.endswith('loadsplitv2')
 s=TB.replace('PENDING_PORTS','.pending_valid(pending_valid),.pending_tag(pending_tag),.pending_done(pending_done),.pending_side(pending_side),' if split else '').replace('WITH_MUL','0' if split else '1').replace('SET_PENDING',"pending_valid=1;pending_tag=packet[279:277];pending_done=0;pending_side={1'b1,32'h00000193,32'h1234abcd};" if split else '').replace('FINISH_PENDING','pending_done=1;' if split else 'mul_ready=1;').replace('EXPECTED_SIDE',"{1'b1,32'h00000193,32'h1234abcd}" if split else "{1'b1,32'h020001b3,32'h1234abcd}").replace('STORE_CASES','' if split else STORE)
 tb=out/'memory_tb.v';tb.write_text(s);iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';tests=[]
 for posted in (0,1):
  for label,cmd in [('compile',[iv,'-g2012','-s','next_memory_tb',f'-Pnext_memory_tb.POSTED={posted}','-o',out/'sim.vvp',src/'nc_memory.v',tb]),('run',[iv.with_name('vvp.exe'),out/'sim.vvp'])]:
   x=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=90);(out/f'{label}_{posted}.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0,(x.stdout+x.stderr).decode(errors='replace')
  tests.append(x.stdout.decode().strip())
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__).resolve(),src/'nc_memory.v',tb]}),indent=2)+'\n');print('\n'.join(tests))
if __name__=='__main__':main()
