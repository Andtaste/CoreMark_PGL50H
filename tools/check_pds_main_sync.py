"""Bind regression benches directly to active PDS RTL, with no trial overrides."""
from pathlib import Path
import json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 active=ROOT/'hardware/pds';receipt=json.loads((ROOT/'docs/pds_main_sync_20261022/prepared.json').read_text(encoding='utf-8'));parent=ROOT/receipt['source_directory'];out=ROOT/'simulation/results/pds_main_sync';out.mkdir(exist_ok=True)
 for n,x in receipt['exact_rtl_mapping'].items():assert sha(active/n)==x['sha256'],n
 actual=[active/n for n in receipt['exact_rtl_mapping']];core=[p for p in actual if p.parent.name=='core'];iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe');model=parent/'pango_ram_wide_models.v';inputs=[*actual,model,Path(__file__).resolve()];tests=[]
 def run(cmd,name):
  x=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(out/name).write_bytes(x.stdout+x.stderr);assert x.returncode==0,(name,(x.stdout+x.stderr)[-3000:]);return x.stdout.decode(errors='replace')
 for kind in ('core','soc'):
  source=parent/f'checks/{kind}_tb.v';tb=out/(kind+'_tb.v');tb.write_bytes(source.read_bytes());inputs.extend((source,tb));files=core if kind=='core' else actual+[model]
  run([iv,'-g2012','-s',kind+'_tb','-o',out/(kind+'.vvp'),*files,tb],kind+'_compile.log')
 for name,kind,seeds in (('random_17','core',(37,613)),('prediction','core',(37,613)),('random_17','soc',(37,)),('soc_faults','soc',(37,))):
  image=ROOT/f'simulation/results/{name}.hex';assert image.exists(),image;inputs.append(image)
  for seed in seeds:
   label=f'{kind}_{name}_{seed}';text=run([vvp,out/(kind+'.vvp'),'+image='+str(image),'+seed='+str(seed),'+trace='+str(out/(label+'.trace')),'+uart='+str(out/(label+'.uart'))],label+'.log');assert 'PASS cycles=' in text,label;tests.append(label+' PASS')
 x=dict(status='PASS',tests=tests,scope='Actual active hardware/pds source list; no isolated-source override. Exact accepted RTL SHA equality plus core variable-latency and posted-enabled SoC integration smoke. Behavioral vendor-compatible wide RAM used here; native PDS compile/map/route separately checks actual vendor IP.',input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs})
 (out/'result.json').write_text(json.dumps(x,indent=2)+'\n');print('PASS active PDS RTL',len(tests),'integration cases')
if __name__=='__main__':main()
