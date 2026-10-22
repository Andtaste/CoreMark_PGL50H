"""Verify independent change scope, exact reconstruction and fixed counters."""
from pathlib import Path
import contextlib,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 out=ROOT/'simulation/results/dual_forward_control_verify';out.mkdir(exist_ok=False);accepted=ROOT/'docs/accepted_dual_baseline.json';a=read(accepted);assert a['variant']=='dual_boundary_storewrite';ref=ROOT/a['source_directory'];inputs=[Path(__file__).resolve(),accepted];tests=[]
 for name,toolname,pattern,changedname,proof,count in (
  ('headmux','generate_dual_forward_control.py',"out=src.with_name('load_bp_'+a.variant)",'nc_operands.v','forward_equivalence',1),
  ('pcselect','generate_dual_pc_select.py',"out=src.with_name('load_bp_dual_boundary_pcselect')",'nc_execute.v','execute_equivalence',2)):
  src=ROOT/('simulation/results/load_bp_dual_boundary_'+name);g=read(src/'generation.json');assert g['accepted_dual_sha256']==sha(accepted);changed=[]
  for n,h in g['override_sha256'].items():
   p=src/Path(n).name;assert sha(p)==h;inputs.append(p)
   if sha(ref/p.name)!=h:changed.append(p.name)
  assert changed==[changedname],changed
  for phase in ('performance','validation'):
   p=src/phase/'result.json';r=ref/phase/'result.json';x=read(p);y=read(r);assert x['status']==y['status']=='PASS'
   for key in ('metrics','predictor','multiply','dual','joint','boundary','mem_ipc','load_queue','store_followers'):assert x[key]==y[key],(name,phase,key)
   inputs +=[p,r];tests.append('PASS '+name+' '+phase+' exact original counters')
  p=src/proof/'result.json';x=read(p);assert x['status']=='PASS' and len(x['tests'])==count;inputs.append(p)
  p=src/'integration_run/result.json';assert read(p)['status']=='PASS';inputs.append(p)
  gen=ROOT/'tools'/toolname;assert sha(gen)==g['generator_sha256'];s=gen.read_text();assert s.count(pattern)==1;target=out/name;s=s.replace(pattern,'out=Path('+repr(str(target))+')');ns={'__file__':str(gen),'__name__':'forward_reproduction'};exec(compile(s,str(gen),'exec'),ns);sys.argv=[str(gen),'--variant','dual_boundary_'+name]
  with (out/(name+'.log')).open('w') as log,contextlib.redirect_stdout(log):ns['main']()
  assert g['override_sha256']==read(target/'generation.json')['override_sha256']
  for p in (src/'ipcore').rglob('*'):
   if p.is_file() and p.suffix in ('.v','.idf'):assert sha(p)==sha(target/'ipcore'/p.relative_to(src/'ipcore'))
  inputs +=[gen,src/'generation.json',target/'generation.json'];tests.append('PASS '+name+' exact RTL/PLL/RAM reconstruction, only '+changedname+' changed')
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print('Independent change scope, exact counters and reconstruction PASS')
if __name__=='__main__':main()
