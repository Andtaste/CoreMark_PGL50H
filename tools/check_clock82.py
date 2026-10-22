"""Physical-top UART timing plus independent fixed-image cycle counters at CLOCK_HZ82."""
from pathlib import Path
import hashlib,json,subprocess,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def linux(p):return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 src=ROOT/'hardware/pds82_seed_sweep';ref=ROOT/'simulation/results/load_bp_dual_boundary_next_pairbranch';out=ROOT/'simulation/results/clock82_checks';out.mkdir(exist_ok=True)
 actual=[p for d in ('core','perips','sys_bus','top','source') for p in sorted((src/'source'/d).glob('*.v'))];model=ref/'pango_ram_wide_models.v';inputs=[*actual,model,Path(__file__).resolve()]
 for p in actual:
  old=ROOT/'hardware/pds'/p.relative_to(src)
  expected=old.read_bytes().replace(b'CLOCK_HZ(80000000)',b'CLOCK_HZ(82000000)') if p.name=='top.v' else old.read_bytes()
  assert p.read_bytes()==expected,p
 def run(cmd,cwd,name,timeout=180):
  x=subprocess.run(list(map(str,cmd)),cwd=cwd,capture_output=True,timeout=timeout);(out/name).write_bytes(x.stdout+x.stderr);assert x.returncode==0,(name,(x.stdout+x.stderr)[-3000:]);return x.stdout.decode(errors='replace')
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe');uarttb=out/'uart82_tb.v'
 uarttb.write_text('''`timescale 1ns/1ps
module pll(input clkin1,output clkout0,pll_lock);assign clkout0=clkin1;assign pll_lock=1'b1;endmodule
module uart82_tb;
 reg clk=0,rst=0;always #6.097561 clk=~clk;wire tx;wire[1:0] gpio;
 top dut(.clk(clk),.rst_ext_i(rst),.uart_rx_pin(1'b1),.uart_tx_pin(tx),.halted_ind(),.gpio(gpio),.jtag_TCK(1'b0),.jtag_TMS(1'b0),.jtag_TDI(1'b0),.jtag_TDO());
 integer i,k;reg[9:0] frame=10'b1101001010;
 initial begin
 repeat(4) @(negedge clk);rst=1;repeat(8) @(negedge clk);
 if(dut.soc.bus.CLOCK_HZ!=82000000 || dut.soc.bus.uart.DIV!=712) $fatal(1,"CLOCK_HZ82/UART712 mismatch");
 force dut.soc.bus.uart_send=1'b1;force dut.soc.bus.dw=32'ha5;
 @(negedge clk);release dut.soc.bus.uart_send;release dut.soc.bus.dw;
 for(i=0;i<10;i=i+1) for(k=0;k<712;k=k+1) begin
 if(tx!==frame[i]) $fatal(1,"UART82 frame mismatch bit=%0d cycle=%0d",i,k);@(negedge clk);
 end
 if(tx!==1 || !dut.soc.bus.uart.ready) $fatal(1,"UART82 frame incomplete");
 $display("PASS actual top CLOCK_HZ82000000 DIV712 A5 exact-cycle 8N1");$finish;end
 initial begin #200000;$fatal(1,"timeout");end
endmodule
''')
 inputs.append(uarttb);run([iv,'-g2012','-s','uart82_tb','-o',out/'uart.vvp',*actual,model,uarttb],ROOT,'uart_compile.log');text=run([vvp,out/'uart.vvp'],ROOT,'uart.log');assert 'PASS actual top' in text
 save(out/'uart_result.json',dict(status='PASS',tests=[text.strip()],input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs},scope='Actual physical top/SoC/UART; PLL clock shim only; real 82MHz PLL is separately checked by native PDS generated-clock STA.'))
 original=ref/'performance/soc_tb.v';tb=out/'soc_tb.v';s=original.read_text();assert s.count(' nc_soc dut(')==1 and s.count('localparam UART_DIV=8;')==1
 s=s.replace(' nc_soc dut(',' nc_soc #(.CLOCK_HZ(82000000)) dut(').replace('localparam UART_DIV=8;','localparam UART_DIV=9;');tb.write_text(s)
 uart=out/'nc_uart_sim.v';uart.write_text((src/'source/perips/nc_uart.v').read_text().replace('BAUD=115200','BAUD=9375000'))
 compiled=[uart if p.name=='nc_uart.v' else p for p in actual if p.name!='top.v']+[model,tb]
 prefix=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--'];run([*prefix,'verilator','--binary','--timing','-j','4','-Wno-fatal','-DCOREMARK_SIM','--top-module','soc_tb','--Mdir',linux(out/'obj'),*[linux(p) for p in compiled]],ROOT,'verilator_compile.log',600)
 results={}
 for label,path in (('validation','sw/build/coremark_validation_1/coremark.hex'),('performance','sw/build/coremark_performance_10/coremark.hex')):
  image=ROOT/path;stdout=run([*prefix,linux(out/'obj/Vsoc_tb'),'+image='+linux(image),'+trace='+linux(out/(label+'.trace')),'+uart='+linux(out/(label+'.uart')),'+notrace=1','+limit=33000000'],ROOT,label+'.log',600);printed=(out/(label+'.uart')).read_text();assert 'COUNTER_CHECK_PASS' in stdout and 'CRC validation   : PASS' in printed and 'PASS cycles=' in stdout
  metrics={s.split(':',1)[0].strip():s.split(':',1)[1].strip() for s in printed.splitlines() if ':' in s};prior=json.loads((ref/label/'result.json').read_text())
  for key in ('Retired instructions','Retired loads','Retired stores','BJP instructions','seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal'):assert metrics[key]==prior['metrics'][key],(label,key)
  dual=re.search(r'DUAL_WINDOW ([^\r\n]+)',stdout);assert dual
  result=dict(status='PASS',metrics=metrics,dual={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',dual[1])},ipc=int(metrics['Retired instructions'])/int(metrics['Stats window cycles']),input_sha256={str(p.relative_to(ROOT)):sha(p) for p in [*compiled,original,image,Path(__file__).resolve()]})
  save(out/(label+'_result.json'),result);results[label]=result;print('PASS',label,'cycles',metrics['Stats window cycles'],'IPC',result['ipc'],flush=True)
 save(out/'result.json',dict(status='PASS',tests=['Physical UART82 exact 712-cycle 8N1','Fixed1 CRC/counters','Fixed10 CRC/counters'],validation=results['validation'],performance=results['performance'],scope='CLOCK_HZ82 SoC; UART accelerated only outside benchmark for fixed-image checks; unchanged firmware still prints75MHz metadata.'))
if __name__=='__main__':main()
