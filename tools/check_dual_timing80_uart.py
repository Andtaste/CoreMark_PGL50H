"""Elaborate the physical top and verify its actual UART divisor/frame timing."""
from pathlib import Path
import json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/load_bp_dual_boundary_pair';out=src/'uart80';out.mkdir(exist_ok=True);g=json.loads((src/'generation.json').read_text())
 files=[]
 for d in ('core','perips','sys_bus','top','source'):
  for p in sorted((ROOT/'hardware/pds/source'/d).glob('*.v')):files.append(src/p.name if str(p.relative_to(ROOT)) in g['override_sha256'] else p)
 files +=[src/'pango_ram_wide_models.v'];tb=out/'uart80_tb.v';tb.write_text('''`timescale 1ns/1ps
// Clock/reset shim only: PLL frequency itself is independently verified by routed STA.
module pll(input clkin1,output clkout0,pll_lock);assign clkout0=clkin1;assign pll_lock=1'b1;endmodule
module uart80_tb;
 reg clk=0,rst=0;always #6.25 clk=~clk;wire tx;wire[1:0] gpio;
 top dut(.clk(clk),.rst_ext_i(rst),.uart_rx_pin(1'b1),.uart_tx_pin(tx),.halted_ind(),.gpio(gpio),.jtag_TCK(1'b0),.jtag_TMS(1'b0),.jtag_TDI(1'b0),.jtag_TDO());
 integer bit_no,k;reg[9:0] frame=10'b1101001010;
 initial begin
 repeat(4) @(negedge clk);rst=1;repeat(8) @(negedge clk);
 if(dut.soc.bus.CLOCK_HZ!=80000000 || dut.soc.bus.uart.DIV!=694) $fatal(1,"Physical top/UART frequency configuration mismatch");
 force dut.soc.bus.uart_send=1'b1;force dut.soc.bus.dw=32'ha5;
 @(negedge clk);release dut.soc.bus.uart_send;release dut.soc.bus.dw;
 for(bit_no=0;bit_no<10;bit_no=bit_no+1) begin
  for(k=0;k<694;k=k+1) begin
   if(tx!==frame[bit_no]) $fatal(1,"UART80 frame mismatch bit=%0d cycle=%0d",bit_no,k);
   @(negedge clk);
  end
 end
 if(tx!==1 || !dut.soc.bus.uart.ready) $fatal(1,"UART80 did not finish frame");
 $display("PASS physical top CLOCK_HZ=80000000 DIV=694; A5 8N1 exact 694-cycle bits");$finish;
 end
 initial begin #200000;$fatal(1,"timeout");end
 endmodule
''')
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
 def run(cmd,name):
  x=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(out/name).write_bytes(x.stdout+x.stderr);assert x.returncode==0,(x.stdout+x.stderr)[-2000:];return x.stdout.decode(errors='replace')
 run([iv,'-g2012','-s','uart80_tb','-o',out/'sim.vvp',*files,tb],'compile.log');s=run([vvp,out/'sim.vvp'],'run.log');assert 'PASS physical top' in s
 inputs=[Path(__file__).resolve(),*files,tb];(out/'result.json').write_text(json.dumps(dict(status='PASS',tests=[s.strip()],scope='Real physical top/SoC/bus/UART RTL, TX injection; PLL replaced by clock shim for simulation; actual PLL period checked separately by routed STA',input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print(s)
if __name__=='__main__':main()
