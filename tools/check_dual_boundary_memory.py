"""Request stability, error prefix, MMIO ordering and response ownership tests."""
from pathlib import Path
import argparse,json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);out=src/'memory_checks';out.mkdir(exist_ok=True);early=int(not a.variant.endswith('_slot'));reads=int(a.variant.endswith('_read'));tb=out/'memory_tb.v'
 tb.write_text('''`timescale 1ns/1ps
module memory_tb;
 reg clk=0;always #5 clk=~clk;reg rst_n=0,kill=0,valid=0,req_ready=0,rsp_valid=0,rsp_error=0;
 reg[279:0] packet=0;reg[64:0] side_packet=0;reg[31:0] rsp_data=0;
 wire ready,wb_valid,req_valid,req_write,rsp_ready;wire[279:0] wb_packet;wire[64:0] wb_side;
 wire[31:0] req_addr,req_data;wire[3:0] req_mask;reg[68:0] held_req;
 localparam EARLY=EARLY_VALUE,READS=READS_VALUE;
 nc_memory #(.EARLY_REQUEST(EARLY)) m(.clk(clk),.rst_n(rst_n),.kill(kill),.valid(valid),.ready(ready),.packet(packet),.side_packet(side_packet),.wb_valid(wb_valid),.wb_packet(wb_packet),.wb_side(wb_side),
 .mul_tag(),.mul_ready(1'b1),.mul_data(32'b0),.mul_consume(),.req_valid(req_valid),.req_ready(req_ready),.req_addr(req_addr),.req_data(req_data),.req_mask(req_mask),.req_write(req_write),.rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_data(rsp_data),.rsp_error(rsp_error));
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task reset;begin rst_n=0;kill=0;valid=0;req_ready=0;rsp_valid=0;rsp_error=0;tick;rst_n=1;end endtask
 task offer;input[3:0] kind;input[31:0] addr;input[2:0] f3,tag;input fault;begin
  packet=0;packet[279:277]=tag;packet[148:117]=addr;packet[116:85]=32'hfedcba98;packet[10:8]=f3;packet[7:4]=kind;packet[3]=kind==4;packet[15:11]=10;packet[2]=fault;valid=1;#1;
 end endtask
 initial begin
  reset;offer(4,32'h10000004,0,3,0);
  if(!ready || req_valid!==EARLY[0]) $fatal(1,"Initial ownership request timing");
  held_req={req_write,req_mask,req_data,req_addr};tick;
  offer(5,32'h10000008,2,4,0);
  if(!EARLY) held_req={req_write,req_mask,req_data,req_addr};
  repeat(4) begin if(!req_valid || {req_write,req_mask,req_data,req_addr}!==held_req) $fatal(1,"Published load request changed across ownership/backpressure");tick;end
  req_ready=1;tick;rsp_valid=1;rsp_data=32'h12345680;#1;
  if(!ready || !wb_valid || wb_packet[279:277]!=3 || wb_packet[180:149]!=32'hffffff80) $fatal(1,"Older response format/tag");
  if(req_valid!==(EARLY && !READS)) $fatal(1,"Younger store launch policy");
  tick;valid=0;rsp_valid=0;
  if(!(EARLY && !READS)) begin if(!req_valid || !req_write || req_addr!=32'h10000008 || req_data!=32'hfedcba98) $fatal(1,"Registered store payload");tick;end
  rsp_valid=1;#1;if(!wb_valid || wb_packet[279:277]!=4) $fatal(1,"Younger store response ownership");tick;rsp_valid=0;
  $display("PASS blocked read request stable across EX/MEM transfer and ordered store turnover");
  reset;offer(0,0,0,1,1);tick;offer(5,32'h10000010,2,2,0);req_ready=1;#1;
  if(ready || req_valid || !wb_valid || !wb_packet[2]) $fatal(1,"Older held exception authorized younger request");
  tick;kill=1;tick;valid=0;kill=0;
  $display("PASS older held exception blocks younger side effects before WB kill");
  reset;offer(4,32'h30000000,2,5,0);if(req_valid) $fatal(1,"Unknown address launched before MEM");tick;
  offer(5,32'h10000010,2,6,0);if(!req_valid || req_addr!=32'h30000000) $fatal(1,"Old unsent request lost priority");req_ready=1;tick;
  rsp_valid=1;rsp_error=1;#1;
  if(ready || req_valid || !wb_valid || !wb_packet[2] || wb_packet[20:16]!=5) $fatal(1,"Late error prefix violation");tick;rsp_valid=0;kill=1;tick;valid=0;kill=0;
  $display("PASS older late bus error blocks younger local request and preserves cause");
  reset;offer(4,32'h20000004,2,7,0);req_ready=1;#1;if(req_valid) $fatal(1,"MMIO escaped registered MEM boundary");tick;valid=0;
  if(!req_valid || req_addr!=32'h20000004) $fatal(1,"MMIO request missing");tick;rsp_valid=1;rsp_data=1;#1;
  if(!wb_valid || wb_packet[180:149]!=1 || wb_packet[279:277]!=7 || wb_packet[2]) $fatal(1,"MMIO response");tick;rsp_valid=0;
  $display("PASS MMIO uses MEM request with registered result boundary");
  $finish;
 end
 initial begin #10000;$fatal(1,"Memory protocol timeout");end
endmodule
'''.replace('EARLY_VALUE',str(early)).replace('READS_VALUE',str(reads)))
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
 def run(cmd,name):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=90);(out/name).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(p.stdout+p.stderr)[-1500:];return p.stdout.decode(errors='replace')
 run([iv,'-g2012','-s','memory_tb','-o',out/'sim.vvp',src/'nc_memory.v',tb],'compile.log');t=run([vvp,out/'sim.vvp'],'simulation.log');tests=[s for s in t.splitlines() if s.startswith('PASS ')];assert len(tests)==4,t
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__).resolve(),tb,src/'nc_memory.v')}),indent=2)+'\n');print(a.variant,'memory protocol PASS')
if __name__=='__main__':main()
