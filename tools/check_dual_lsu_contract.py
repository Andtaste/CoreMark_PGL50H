"""Independent memory request/response contract and bulk RV32 differential checks."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 variant=sys.argv[1];src=ROOT/('simulation/results/load_bp_'+variant);out=src/'contract_checks';out.mkdir(exist_ok=True)
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe');inputs=[Path(__file__).resolve()];tests=[]
 def run(cmd,name):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(out/name).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(name,(p.stdout+p.stderr)[-2500:]);return p.stdout.decode(errors='replace')
 if variant in ('dual_lsu_forward','dual_lsu_pair'):
  tb=out/'memory_tb.v';text=r'''`timescale 1ns/1ps
module memory_tb;
 reg clk=0;always #5 clk=~clk;reg rst_n=0,kill=0,valid=0;
 reg[279:0] packet=0;reg[96:0] side_packet=0;
 reg req_ready=1,req1_ready=1,req_nofault=0,rsp_valid=0,rsp1_valid=0,rsp_error=0;
 reg[31:0] rsp_data=0,rsp1_data=0;
 wire ready,wb_valid,req_valid,req1_valid,rsp_ready,rsp1_ready;
 wire[279:0] wb_packet;wire[64:0] wb_side;wire[31:0] req_addr,req1_addr;
 wire load0_valid,load1_valid;wire[2:0] load_tag;wire[31:0] load0_data,load1_data;
 nc_memory m(.clk(clk),.rst_n(rst_n),.kill(kill),.valid(valid),.ready(ready),.packet(packet),.side_packet(side_packet),.wb_valid(wb_valid),.wb_packet(wb_packet),.wb_side(wb_side),
 .mul_ready(1'b1),.mul_data(32'b0),.mul_tag(),.mul_consume(),.req_valid(req_valid),.req_ready(req_ready),GRANT.req_addr(req_addr),.req_data(),.req_mask(),.req_write(),
 .rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_data(rsp_data),.rsp_error(rsp_error),.req1_valid(req1_valid),.req1_ready(req1_ready),.req1_addr(req1_addr),.req1_data(),.req1_mask(),.req1_write(),
 .rsp1_valid(rsp1_valid),.rsp1_ready(rsp1_ready),.rsp1_data(rsp1_data),.load0_valid(load0_valid),.load1_valid(load1_valid),.load_tag(load_tag),.load0_data(load0_data),.load1_data(load1_data));
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task reset;begin rst_n=0;valid=0;req_ready=1;req1_ready=1;req_nofault=0;rsp_valid=0;rsp1_valid=0;rsp_error=0;tick;rst_n=1;end endtask
 task group;input store_side;input[31:0] addr;begin
  packet=0;packet[279:277]=3'd5;packet[7:4]=4;packet[3]=1;packet[15:11]=10;packet[10:8]=2;packet[148:117]=32'h10000000;
  side_packet={1'b1,(store_side ? 32'h00b42023 : 32'h00042603),32'h11223344,addr};valid=1;#1;
 end endtask
 initial begin
  reset;group(1,32'h10000010);
  if(!req_valid || req1_valid || !ready) $fatal(1,"Store requires older response without guarantee");
  tick;valid=0;repeat(3) begin if(req1_valid) $fatal(1,"Premature store");tick;end
  rsp_valid=1;rsp_error=1;#1;
  if(req1_valid || !wb_valid || !wb_packet[2] || wb_side[64]) $fatal(1,"Fault must suppress side store");
  tick;rsp_valid=0;rsp_error=0;
  if(load0_valid || load1_valid) $fatal(1,"Fault leaked a completion");
  $display("PASS no-grant late primary error cancels younger store");
  reset;group(0,32'h10000010);if(!req_valid || !req1_valid) $fatal(1,"Speculative clean RAM read not offered");
  tick;valid=0;rsp1_valid=1;rsp1_data=32'h87654321;#1;if(load1_valid) $fatal(1,"Combinational return");
  tick;rsp1_valid=0;if(load1_valid) $fatal(1,"Younger load exposed before primary success");
  rsp_valid=1;rsp_error=0;rsp_data=32'hfedcba98;#1;if(load0_valid || load1_valid) $fatal(1,"Raw response bypass");
  tick;rsp_valid=0;
  if(!load0_valid || !load1_valid || load_tag!=5 || load0_data!=32'hfedcba98 || load1_data!=32'h87654321) $fatal(1,"Registered completion values/tag");
  tick;if(load0_valid || load1_valid) $fatal(1,"Completion pulse repeated");
  $display("PASS registered result buses retain early side data until older success");
  reset;req1_ready=0;group(0,32'h10000010);tick;valid=0;
  rsp_valid=1;rsp_error=1;#1;if(wb_valid || !req1_valid) $fatal(1,"Offered read must remain stable and drain on fault");
  tick;rsp_valid=0;req1_ready=1;#1;if(!req1_valid) $fatal(1,"Offered request withdrawn");
  tick;req1_ready=0;rsp1_valid=1;rsp1_data=32'h99999999;#1;
  if(!wb_valid || !wb_packet[2] || wb_side[64]) $fatal(1,"Fault drainage result");
  tick;rsp1_valid=0;if(load0_valid || load1_valid) $fatal(1,"Fault drain leaked result");
  $display("PASS pending offered read stable through older error and drained before fault WB");
  GUARANTEE_TEST
  $finish;
 end
 initial begin #10000;$fatal(1,"Memory unit timeout");end
endmodule
'''
  grant=''
  if variant=='dual_lsu_pair':
   grant=r'''
  reset;req_nofault=1;group(1,32'h10000010);if(!req_valid || !req1_valid) $fatal(1,"Explicit guarantee did not allow parallel store");
  tick;valid=0;rsp_valid=1;rsp_data=32'h76543210;tick;rsp_valid=0;
  if(!load0_valid || load0_data!=32'h76543210 || wb_valid) $fatal(1,"Older registered return must precede younger store completion");
  rsp1_valid=1;#1;if(!wb_valid || !wb_side[64] || wb_packet[2]) $fatal(1,"Guaranteed dual memory WB");tick;rsp1_valid=0;
  reset;req_nofault=1;group(1,32'h10000004);if(req1_valid) $fatal(1,"Guarantee bypassed physical line alias");
  tick;valid=0;rsp_valid=1;rsp_data=32'h12345678;#1;if(!req1_valid) $fatal(1,"Alias not released after response");
  tick;rsp_valid=0;rsp1_valid=1;tick;rsp1_valid=0;
  $display("PASS guaranteed parallel store and 64-bit physical-line alias serialization");
'''
  tb.write_text(text.replace('GRANT','.req_nofault(req_nofault),' if grant else '').replace('GUARANTEE_TEST',grant));inputs +=[tb,src/'nc_memory.v']
  run([iv,'-g2012','-s','memory_tb','-o',out/'memory.vvp',src/'nc_memory.v',tb],'unit_compile.log');t=run([vvp,out/'memory.vvp'],'unit.log');tests+=t.strip().splitlines()
 # A memory-intensive program without traps permits full architectural reference comparison.
 sys.path.insert(0,str(ROOT/'simulation/scripts/run'));import regression
 asm=ROOT/'simulation/research/dual_lsu/pair_lsu.S';s=asm.read_text();s=s[:s.index(' jal zero,case_bad_store')];s=s.replace(' la t0,handler\n csrw mtvec,t0\n','')
 s+='\n li t0,0x20003000\n li t1,1\n sw t1,0(t0)\ndone: j done\n'
 source=out/'bulk.S';source.write_text(s);gcc=regression.find('riscv-none-elf-gcc',Path('D:/Program Files/riscv').glob('**/riscv-none-elf-gcc.exe'));old=regression.OUT;regression.OUT=out
 try:image,data=regression.build(gcc,source,'bulk')
 finally:regression.OUT=old
 g=json.loads((src/'generation.json').read_text());files=sorted((ROOT/'hardware/pds/source/core').glob('*.v'));files=[src/p.name if str(p.relative_to(ROOT)) in g['override_sha256'] else p for p in files];tb=src/'checks/core_tb.v';inputs +=[asm,source,image,tb,*files]
 run([iv,'-g2012','-s','core_tb','-o',out/'bulk.vvp',*files,tb],'bulk_compile.log')
 for seed in (37,613,2026):
  trace=out/f'bulk_{seed}.trace';t=run([vvp,out/'bulk.vvp',f'+image={image}',f'+trace={trace}',f'+seed={seed}'],f'bulk_{seed}.log');assert 'PASS cycles=' in t;regression.differential(data,trace);tests.append(f'PASS full memory/subword/alias architectural differential seed={seed}')
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print(variant,'contract PASS',len(tests))
if __name__=='__main__':main()
