"""Additional two-issue ownership, RF, cancellation and burst checks."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'simulation/results/load_bp_dual_issue'
sys.path.insert(0,str(ROOT/'simulation/scripts/run'));import regression
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 dest=OUT/'dual_checks';dest.mkdir(exist_ok=True)
 meta=json.loads((OUT/'generation.json').read_text());overrides=meta['override_sha256'];inputs=[Path(__file__).resolve()]
 for n,h in overrides.items():assert sha(OUT/Path(n).name)==h,n
 guard={p:sha(p) for p in (ROOT/'docs/accepted_baseline.json',ROOT/'hardware/pds/report_timing/top.rtr')}
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
 def run(cmd,name):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(dest/name).write_bytes(p.stdout+p.stderr)
  assert p.returncode==0,(name,(p.stdout+p.stderr)[-4000:]);return p.stdout.decode(errors='replace')
 unit=ROOT/'simulation/research/dual_issue/dual_units_tb.v';rtl=[OUT/'nc_fetch.v',OUT/'nc_regfile.v',ROOT/'hardware/pds/source/core/nc_btb.v'];inputs+=[unit,*rtl]
 run([iv,'-g2012','-s','dual_units_tb','-o',dest/'unit.vvp',*rtl,unit],'unit_compile.log')
 t=run([vvp,dest/'unit.vvp'],'unit.log');assert 'PASS dual units cycles=30000' in t
 tests=[t.strip()];coverage=[]
 gcc=regression.find('riscv-none-elf-gcc',Path('D:/Program Files/riscv').glob('**/riscv-none-elf-gcc.exe'))
 src=ROOT/'simulation/research/dual_issue/dual_faults.S';old=regression.OUT;regression.OUT=dest
 try:image,data=regression.build(gcc,src,'dual_faults')
 finally:regression.OUT=old
 inputs+=[src,image]
 for kind,seeds in (('core',(37,613)),('soc',(0,))):
  executable=OUT/'checks'/(kind+'.vvp')
  inputs+=[OUT/'checks'/(kind+'_tb.v')]
  for seed in seeds:
   trace=dest/f'{kind}_{seed}.trace'
   t=run([vvp,executable,f'+image={image}',f'+trace={trace}',f'+seed={seed}',f'+uart={dest}/unused_uart.txt'],f'{kind}_{seed}.log');assert 'PASS cycles=' in t
   causes=[int(s.split()[-1],16) for s in trace.read_text().splitlines() if s.split()[4]=='1'];assert causes==[5,7,4],causes
   m=re.search(r'DUAL_STATS ([^\r\n]+)',t);assert m
   c={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])}
   assert c['fault_cancelled']>=2,c
   if kind=='soc':assert c['max_dual_streak']>=16,c
   coverage.append(dict(kind=kind,seed=seed,**c));tests.append(f'{kind} dual fault/RAW/WAW/WAR/burst seed={seed} PASS')
 # Counters must support retirement > cycles too, even if CoreMark IPC<1.
 stats=dest/'stats_dual_tb.v';stats.write_text('''`timescale 1ns/1ps
module stats_dual_tb;
 reg clk=0;always #5 clk=~clk;reg rst_n=0,control=0;reg[31:0] control_data=0;reg[13:0] events=0;
 wire[31:0] data;nc_stats s(.clk(clk),.rst_n(rst_n),.control(control),.control_data(control_data),.events(events),.addr(4'd9),.data(data));
 initial begin
  repeat(3) @(negedge clk);rst_n=1;control=1;control_data=3;
  @(negedge clk);control=0;events=(1<<0)|(1<<8)|(1<<9);
  repeat(100) @(negedge clk);control=1;control_data=0;events=0;
  @(negedge clk);control=0;
  if(s.counters[1]!=100 || s.counters[9]!=200 || s.counters[10]!=100) $fatal(1,"Dual stats count > cycles failed");
  control=1;control_data=3;@(negedge clk);control=0;events=(1<<8)|(1<<9);
  s.counters[9]=32'hfffffffe;
  repeat(2) @(negedge clk);control=1;control_data=0;events=0;
  @(negedge clk);control=0;
  if(!s.overflow[8] || s.counters[9]!=2) $fatal(1,"Dual stats carry/overflow failed");
  $display("PASS dual stats >1 IPC and two-instruction overflow");$finish;
 end
endmodule
''')
 inputs+=[stats,OUT/'nc_stats.v']
 run([iv,'-g2012','-s','stats_dual_tb','-o',dest/'stats.vvp',OUT/'nc_stats.v',stats],'stats_compile.log')
 t=run([vvp,dest/'stats.vvp'],'stats.log');assert 'PASS dual stats' in t;tests.append(t.strip())
 for p,h in guard.items():assert sha(p)==h,p
 for n,h in overrides.items():assert sha(OUT/Path(n).name)==h,n
 x=dict(status='PASS',tests=tests,coverage=coverage,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs},override_sha256=overrides)
 (dest/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({k:v for k,v in x.items() if k not in ('input_sha256','override_sha256')},indent=2))
if __name__=='__main__':main()
