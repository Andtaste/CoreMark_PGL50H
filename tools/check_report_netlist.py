"""Replay exact report code in the ADS structural netlist (untimed)."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
from check_report_large import ROOT,OUT,linux,run
def main():
 project=ROOT/(sys.argv[1] if len(sys.argv)>1 else 'hardware/pds')
 s=(project/'synthesize/top_syn.vm').read_text()
 logic_hash=hashlib.sha256(re.sub(r'//[^\n]*','',s).encode()).hexdigest()
 old=[int(x,16) for x in (project/'memory/boot.hex').read_text().split()]
 new=[int(x,16) for x in (OUT/'exact.hex').read_text().split()]
 block=re.search(r'module ipml_dpram_v1_6_ram1_tdp\b.*?endmodule',s,re.S)[0];count=0
 def patch(m):
  nonlocal count
  body,j,i=m[1],int(m[2]),int(m[3]);count+=1
  def init(n):
   idx=int(n[1],16)
   def value(words):return sum(((words[j*2048+idx*32+k]>>(8*i))&255)<<(9*k) for k in range(32))
   assert int(n[2],2)==value(old),(j,i,idx)
   return f'.INIT_{n[1]}(288\'b{value(new):0288b})'
  changed,num=re.subn(r"\.INIT_([0-9A-F]{2})\(288'b([01]+)\)",init,body);assert num==64,(j,i,num)
  return changed+'\n        '+m[4]
 pattern=r'(GTP_DRM18K\b.*?)(\\ADDR_LOOP\[(\d+)\])'
 # Capture bank indices while preserving the complete primitive name.
 pattern=r'(GTP_DRM18K\b.*?#\(.*?\))\s*(\\ADDR_LOOP\[(\d+)\]\.DATA_LOOP\[(\d+)\]\.U_GTP_DRM18K)'
 def adapter(m):
  class Match:
   def __getitem__(self,k):return {1:m[1],2:m[3],3:m[4],4:m[2]}[k]
  return patch(Match())
 patched=re.sub(pattern,adapter,block,flags=re.S);assert count==32,count;s=s.replace(block,patched)
 s=re.sub(r'module pll\b.*?endmodule','module pll(input clkin1,output clkout0,pll_lock);assign clkout0=clkin1;assign pll_lock=1;endmodule',s,flags=re.S)
 # Only peripheral wait/printing is accelerated. CPU/memory netlist untouched.
 uart=r'''module nc_uart(input [279:0] \soc/cpu/memory_packet ,input N5,clk,send,output [3:0] bits_left,output ready,tx);
assign bits_left=0;assign ready=1;assign tx=1;
integer fd;initial fd=$fopen("simulation/results/report_large_20261023/netlist.uart","w");
always @(posedge clk) if(send) begin $fwrite(fd,"%c",\soc/cpu/memory_packet [92:85]);$fflush(fd);end
endmodule'''
 s=re.sub(r'module nc_uart\b.*?endmodule',lambda m:uart,s,flags=re.S)
 net=OUT/'replay_netlist.v';net.write_text(s)
 tb=OUT/'gate_tb.v';tb.write_text('''`timescale 1ns/1ps
module gate_tb;
reg clk=0,rst=0;always #5 clk=~clk;wire done;wire[1:0] gpio;
GTP_GRS GRS_INST(.GRS_N(1'b1));
top dut(.clk(clk),.rst_ext_i(rst),.uart_rx_pin(1'b1),.uart_tx_pin(),.halted_ind(done),.gpio(gpio),.jtag_TCK(1'b0),.jtag_TMS(1'b0),.jtag_TDI(1'b0),.jtag_TDO());
initial begin repeat(10) @(negedge clk);rst=1;end
reg[31:0] original_code[0:16383];initial $readmemh("simulation/results/report_large_20261023/exact.hex",original_code);
task check_compare(input[203:0] packet,input[18:0] control,input[31:0] result,input taken,input lane);
reg[31:0] a,b,insn;reg expected;reg[2:0] f3;
begin
insn=original_code[packet[199:170]];
a=packet[135:104];b=insn[6:0]==7'h13 ? {{20{insn[31]}},insn[31:20]} : packet[103:72];f3=insn[14:12];
if((insn[6:0]==7'h13 || insn[6:0]==7'h33) && (f3==2 || f3==3) && insn[31:25]!=1) begin
expected=f3==2 ? ((a[31]!=b[31])?a[31]:(a<b)) : (a<b);
if(result!={31'b0,expected}) $display("COMPARE_MISMATCH lane=%d pc=%h ctrl=%h a=%h b=%h result=%h expected=%d",lane,packet[199:168],control,a,b,result,expected);
end
if(insn[6:0]==7'h63) begin
case(f3) 0:expected=a==b;1:expected=a!=b;4:expected=(a[31]!=b[31])?a[31]:(a<b);5:expected=(a[31]!=b[31])?!a[31]:(a>=b);6:expected=a<b;7:expected=a>=b;default:expected=0;endcase
if(taken!==expected) $display("BRANCH_MISMATCH lane=%d pc=%h f3=%d a=%h b=%h taken=%d expected=%d",lane,packet[199:168],f3,a,b,taken,expected);
end
end endtask
always @(posedge clk) if(rst && dut.soc.cpu.ex_fire) begin
check_compare(dut.soc.cpu.ex_packet,dut.soc.cpu.ex_control,dut.soc.cpu.execute_packet[180:149],dut.soc.cpu.execute_taken,0);
if(dut.soc.cpu.side_execute) check_compare(dut.soc.cpu.ex_side[203:0],dut.soc.cpu.ex_side[222:204],dut.soc.cpu.secondary_result[180:149],dut.soc.cpu.execute1.taken,1);
end
integer cycles=0;always @(posedge clk) begin cycles<=cycles+1;
if(cycles%10000==0) begin $display("GATE_PROGRESS cycles=%0d pc=%h insn=%h",cycles,dut.soc.cpu.id_pc,dut.soc.cpu.id_insn);$fflush();end
if(done) begin $display("PASS netlist report replay cycles=%0d",cycles);$finish;end if(cycles>300000) $fatal(1,"gate replay timeout");end
endmodule
''')
 vendor=Path('E:/pango/PDS_2022.2-SP1-Lite/arch/vendor/pango/verilog/simulation')
 adapters=OUT/'lut_mux_adapters.v';adapters.write_text('''// Two-state equivalents of the vendor UDP mux tables for Verilator.
module INT_LUTMUX2_UDP(output dout,input sel,di1,di0);assign dout=sel?di1:di0;endmodule
module INT_LUTMUX4_UDP(output dout,input s1,s0,di3,di2,di1,di0);assign dout=s1?(s0?di3:di2):(s0?di1:di0);endmodule
''')
 local=OUT/'vendor_mux';local.mkdir(exist_ok=True)
 for f in vendor.glob('GTP_*.v'):
  text=f.read_text(errors='replace')
  if re.search(r'INT_LUTMUX[24]_UDP\s*\(',text):
   counter=[0]
   def named(m):
    counter[0]+=1;return m[1]+f' adapter_mux_{counter[0]} ('
   (local/f.name).write_text(re.sub(r'(INT_LUTMUX[24]_UDP)\s*\(',named,text))
 prefix=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--']
 run([*prefix,'verilator','--binary','--timing','-j','4','-Wno-fatal','--top-module','gate_tb','--Mdir',linux(OUT/'gate_obj'),'-y',linux(local),'-y',linux(vendor),linux(adapters),linux(net),linux(tb)],OUT/'gate_compile.log')
 text=run([*prefix,linux(OUT/'gate_obj/Vgate_tb')],OUT/'gate.log');assert 'PASS netlist report replay' in text
 uart=(OUT/'netlist.uart').read_text();print(uart)
 if '--require-correct' in sys.argv:
  assert 'MISMATCH' not in text
  for expected in ('Iterations/Sec   : 360.941214','IPC                : 1.105','CPI                : 0.904','Counter bounds     : PASS'):
   assert expected in uart,expected
  (project/'report_replay.uart').write_text(uart)
  (project/'report_replay.log').write_text(text,encoding='utf-8')
  (project/'report_replay.json').write_text(json.dumps({'status':'PASS','netlist_logic_sha256':logic_hash,'execute_sha256':hashlib.sha256((project/'source/core/nc_execute.v').read_bytes()).hexdigest(),'scope':'Exact firmware report replay with board counters, accelerated peripherals and untimed vendor primitives; no comparison mismatches.'},indent=2)+'\n')
if __name__=='__main__':main()
