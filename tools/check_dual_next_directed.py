"""New-pair and staggered-execution directed programs on slow core and real SoC."""
from pathlib import Path
import argparse,json,hashlib,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'simulation/scripts/run'));import regression
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);out=src/'next_directed';out.mkdir(exist_ok=True);g=json.loads((src/'generation.json').read_text());inputs=[Path(__file__).resolve()]
 rtl=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[]);actual=[src/p.name if str(p.relative_to(ROOT)) in g['override_sha256'] else p for p in rtl];model=src/'pango_ram_wide_models.v';inputs+=actual+[model]
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe'
 def run(cmd,log):
  x=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(out/log).write_bytes(x.stdout+x.stderr);assert x.returncode==0,(log,(x.stdout+x.stderr).decode(errors='replace')[-2500:]);return x.stdout.decode(errors='replace')
 gcc=regression.find('riscv-none-elf-gcc',Path('D:/Program Files/riscv').glob('**/riscv-none-elf-gcc.exe'));images={}
 for name in ('pair_memory','pair_memory_fault'):
  source=ROOT/f'simulation/research/dual_next/{name}.S';old=regression.OUT;regression.OUT=out
  try:images[name]=regression.build(gcc,source,name)
  finally:regression.OUT=old
  inputs +=[source,images[name][0]]
 mon='''
 integer np_mul=0,np_branch=0,np_split=0,np_early=0;
 always @(posedge clk) if(rst_n) begin
  if(CPU.pair_issue && (CPU.id_kind==4 || CPU.id_kind==5)) begin
   if(CPU.id_side_kind==6) np_mul=np_mul+1;
   if(CPU.id_side_kind==1) np_branch=np_branch+1;
  end
  SPLIT_COVER
  EARLY_COVER
 end
 always @(negedge clk) if(finish_count==1) $display("NEXT_DIRECTED mul=%0d branch=%0d split=%0d early=%0d",np_mul,np_branch,np_split,np_early);
 '''
 for kind in ('core','soc'):
  cpu='dut' if kind=='core' else 'dut.cpu';bench=src/('checks' if (src/'checks').exists() else 'smoke')/(kind+'_tb.v');s=bench.read_text();inputs.append(bench)
  block=mon.replace('SPLIT_COVER','if(CPU.split_begin) np_split=np_split+1;' if 'split_begin' in (src/'nc_core.v').read_text() else '').replace('EARLY_COVER','if(CPU.primary_mul_early && !CPU.ex_fire) np_early=np_early+1;' if 'primary_mul_early' in (src/'nc_core.v').read_text() else '')
  tb=out/(kind+'_tb.v');tb.write_text(s.replace('endmodule',block.replace('CPU',cpu)+'\nendmodule'));inputs.append(tb);files=[p for p in actual if p.name in {q.name for q in (ROOT/'hardware/pds/source/core').glob('*.v')}] if kind=='core' else actual+[model]
  run([iv,'-g2012','-s',kind+'_tb','-o',out/(kind+'.vvp'),*files,tb],kind+'_compile.log')
 tests=[];coverage=[]
 for name,(image,data) in images.items():
  for kind,seeds in (('core',(37,613)),('soc',(0,))):
   for seed in seeds:
    trace=out/f'{name}_{kind}_{seed}.trace';s=run([iv.with_name('vvp.exe'),out/(kind+'.vvp'),f'+image={image}',f'+trace={trace}',f'+seed={seed}',f'+uart={out}/unused_uart.txt'],f'{name}_{kind}_{seed}.log');assert 'PASS cycles=' in s
    if name=='pair_memory':regression.differential(data,trace)
    else:
     causes=[int(z.split()[-1],16) for z in trace.read_text().splitlines() if z.split()[4]=='1'];assert causes==[5,7,5,7],causes
    m=re.search(r'NEXT_DIRECTED ([^\r\n]+)',s);assert m;c={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])};coverage.append(dict(program=name,kind=kind,seed=seed,**c));tests.append(name+' '+kind+' '+str(seed)+' PASS')
 if a.variant.endswith('pairmul'):assert sum(c['mul'] for c in coverage)>0
 if a.variant.endswith('pairbranch'):assert sum(c['branch'] for c in coverage)>0
 if a.variant.endswith('mpre'):assert sum(c['early'] for c in coverage)>0
 if a.variant.endswith('loadsplitv2'):assert sum(c['split'] for c in coverage)>0
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,coverage=coverage,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print(json.dumps(coverage,indent=2))
if __name__=='__main__':main()
