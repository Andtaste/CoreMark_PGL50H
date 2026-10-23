"""Differential local-bus protocol test with boundary addresses and backpressure."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'simulation/results/autonomous_20261022'

def main():
 ap=argparse.ArgumentParser();ap.add_argument('name');a=ap.parse_args()
 src=WORK/a.name;parent=json.loads((src/'parent_baseline.json').read_text())
 ref=ROOT/parent['project_directory'];out=src/'bus_lockstep';out.mkdir(exist_ok=True)
 golden=out/'golden_bus.v'
 golden.write_text((ref/'source/sys_bus/nc_local_bus.v').read_text().replace('module nc_local_bus','module golden_bus'))
 tb='''module bus_tb;
 reg clk=0;always #5 clk=!clk;
 reg rst_n=0,iv=0,ior=0,dv=0,dor=0,dwrite=0;
 reg[31:0] ia=0,da=0,dw=0;reg[3:0] dm=0;
 wire[1:0] ir,iov,ierr,dr,dov,derr,uart,timer;
 wire[63:0] idata[0:1];wire[31:0] ddata[0:1],tohost[0:1];wire[1:0] gpio[0:1];
 reg[31:0] rng;integer seed,ticks=0,reads=0,writes=0,errors=0;
 function[31:0] address(input[31:0] v);
  case(v[4:0])
   0:address=0;1:address=32'hfffc;2:address=32'hffff;3:address=32'h10000;
   4:address=32'h0ffffffc;5:address=32'h10000000;6:address=32'h10007ffc;
   7:address=32'h10007fff;8:address=32'h10008000;9:address=32'h10010000;
   10:address=32'h20000000;11:address=32'h20000004;
   12:address=32'h20001000;13:address=32'h20001004;
   14:address=32'h20001008;15:address=32'h2000100c;
   16:address=32'h20002000;17:address=32'h20003000;
   18:address=32'h20003004;19:address=32'hffffffff;
   20:address=32'h80000000;21:address=32'h90000000;
   default:address=v;
  endcase
 endfunction
 initial begin seed=37;if($value$plusargs("seed=%d",seed)) begin end rng=seed;end
 always @(negedge clk) begin
  if(rst_n) begin
   if({ir[0],iov[0],ierr[0],dr[0],dov[0],derr[0],uart[0],timer[0],gpio[0],tohost[0]} !==
      {ir[1],iov[1],ierr[1],dr[1],dov[1],derr[1],uart[1],timer[1],gpio[1],tohost[1]})
      $fatal(1,"Bus control mismatch cycle=%0d",ticks);
   if(iov[0] && idata[0]!==idata[1]) $fatal(1,"IF data mismatch");
   if(dov[0] && ddata[0]!==ddata[1]) $fatal(1,"Data response mismatch");
   if(dv && dr[0]) begin if(dwrite) writes=writes+1;else reads=reads+1;end
   if(dov[0] && derr[0]) errors=errors+1;
  end
  ticks=ticks+1;
  if(ticks==30000) begin
   if(reads<100 || writes<100 || errors<100) $fatal(1,"Insufficient exercised traffic");
   $display("BUS_LOCKSTEP_PASS cycles=%0d reads=%0d writes=%0d errors=%0d",ticks,reads,writes,errors);$finish;
  end
  rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
  rst_n <= ticks>3 && ticks%3001!=0;
  ior<=rng[6];dor<=rng[7];
  if(!rst_n) begin iv<=0;dv<=0;dwrite<=0;end
  else begin
   if(!iv || ir[0]) begin iv<=rng[8];ia<=address({rng[15:0],rng[31:16]});end
   if(!dv || dr[0]) begin dv<=rng[9];dwrite<=rng[9] && rng[10];da<=address(rng);dw<=rng;dm<=rng[14:11];end
  end
 end
 INSTANCES
endmodule
'''
 instances=[]
 for i,module in enumerate(('nc_local_bus','golden_bus')):
  ports=['.clk(clk)','.rst_n(rst_n)']+[f'.{x}({x})' for x in ('iv','ia','ior','dv','da','dw','dm','dwrite','dor')]+['.wa(da)']
  ports += [f'.{x}({x}[{i}])' for x in ('ir','iov','idata','ierr','dr','dov','ddata','derr','tohost')]
  ports += [f'.uart_tx(uart[{i}])',f'.timer_irq(timer[{i}])',f'.gpio_out(gpio[{i}])']
  instances.append(f'{module} #(.CLOCK_HZ(1000000)) dut{i}('+','.join(ports)+');')
 bench=out/'bus_tb.v';bench.write_text(tb.replace('INSTANCES','\n'.join(instances)))
 model=ROOT/f'simulation/results/load_bp_dual_boundary_auto_{a.name}/pango_ram_wide_models.v'
 files=[src/'source/sys_bus/nc_local_bus.v',src/'source/perips/nc_uart.v',golden,model,bench]
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
 def run(cmd,name):
  result=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180)
  (out/f'{name}.log').write_bytes(result.stdout+result.stderr)
  assert result.returncode==0,(name,result.stdout[-1000:],result.stderr[-1000:])
  return result.stdout
 run([iv,'-g2012','-s','bus_tb','-o',out/'sim.vvp',*files],'compile')
 for seed in (37,613,2026):
  assert b'BUS_LOCKSTEP_PASS' in run([vvp,out/'sim.vvp',f'+seed={seed}'],f'seed_{seed}')
 (out/'result.json').write_text(json.dumps(dict(status='PASS',cycles_per_seed=30000,seeds=[37,613,2026],scope='Parent bus differential: full-range boundary/alias/MMIO addresses, byte writes, concurrent IF, stalls and reset',input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}),indent=2)+'\n')
 print(a.name,'PASS 90000 bus lockstep cycles')

if __name__=='__main__':main()
