"""Current dual-issue benches: core/SoC differential plus all47 ISA fixtures."""
from pathlib import Path
import json,subprocess,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'simulation/scripts/run'));import regression
def main():
 src=ROOT/'simulation/results/report_compare_fix83_20261023';out=src/'checks';out.mkdir(exist_ok=True)
 reference=ROOT/'simulation/results/load_bp_dual_boundary_auto_mul_early_products'
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
 def run(cmd,name):
  with (out/(name+'.log')).open('wb') as f:r=subprocess.run(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=240)
  text=(out/(name+'.log')).read_text(errors='replace');assert r.returncode==0,(name,text[-1000:]);return text
 core=sorted((src/'source/core').glob('*.v'));soc=core+[p for d in ('perips','sys_bus','top') for p in (src/'source'/d).glob('*.v')]
 for kind,rtl in [('core',core),('soc',soc+[ROOT/'simulation/models/pango_ram_wide_models.v'])]:run([iv,'-g2012','-s',kind+'_tb','-o',out/(kind+'.vvp'),*rtl,reference/'checks'/(kind+'_tb.v')],kind+'_compile')
 tests=[]
 for kind,names,seeds in [('core',('directed','random_17','random_91','random_2026','prediction'),(37,613)),('soc',('prediction','throughput','soc_faults','random_17','random_91','random_2026'),(0,))]:
  for name in names:
   data=(ROOT/f'simulation/results/{name}.bin').read_bytes();data+=bytes(65536-len(data))
   for seed in seeds:
    label=f'{kind}_{name}_{seed}';trace=out/(label+'.trace')
    text=run([vvp,out/(kind+'.vvp'),f'+image={ROOT}/simulation/results/{name}.hex',f'+trace={trace}',f'+seed={seed}',f'+uart={out}/unused.uart'],label);assert 'PASS cycles=' in text
    if name not in ('directed','soc_faults'):regression.differential(data,trace)
    else:
     causes=[int(s.split()[-1],16) for s in trace.read_text().splitlines() if s.split()[4]=='1']
     expected=[5,0,0,3,1,7,0x80000007] if name=='soc_faults' else [4,6,5,7,2,11,2,0x80000003,0x80000007,0x8000000b]
     assert causes==expected,(label,causes)
    tests.append(label);print('PASS',label,flush=True)
 fixtures=sorted((ROOT/'references/isa/generated').glob('*.bin'));assert len(fixtures)==47
 for f in fixtures:
  b=f.read_bytes();b+=bytes(65536-len(b));image=out/'isa.hex';image.write_text(''.join(f'{int.from_bytes(b[i:i+4],"little"):08x}\n' for i in range(0,65536,4)))
  text=run([vvp,out/'soc.vvp',f'+image={image}',f'+trace={out}/{f.stem}.trace',f'+uart={out}/unused.uart','+legacy=1','+limit=100000'],f.stem);assert 'PASS cycles=' in text;tests.append(f.stem)
 assert len(tests)==63
 (out/'result.json').write_text(json.dumps({'status':'PASS','tests':tests,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in soc}},indent=2))
 print('PASS all63 current dual-issue core/SoC/ISA tests',flush=True)
if __name__=='__main__':main()
