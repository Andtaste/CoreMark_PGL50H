"""Verify observer transparency, changed-source scope, and exact reconstruction."""
from pathlib import Path
import contextlib,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 out=ROOT/'simulation/results/dual_mul_tail_verify';out.mkdir(exist_ok=False);accepted=ROOT/'docs/accepted_dual_baseline.json';d=read(accepted);assert d['variant']=='dual_boundary_storewrite';ref=ROOT/d['source_directory'];original=read(ref/'performance/result.json');inputs=[Path(__file__).resolve(),accepted,ref/'performance/result.json'];tests=[];names=('mulprobe','pairprobe','multail','mullowtail')
 for name in names:
  src=ROOT/('simulation/results/load_bp_dual_boundary_'+name);g=read(src/'generation.json');assert g['accepted_dual_sha256']==sha(accepted);changed=[]
  for key,h in g['override_sha256'].items():
   p=src/Path(key).name;assert sha(p)==h;inputs.append(p)
   if sha(ref/p.name)!=h:changed.append(p.name)
  assert changed==([] if name in ('mulprobe','pairprobe') else ['nc_mul_pipeline.v']),changed
  if name in ('mulprobe','pairprobe'):
   x=read(src/'performance/result.json')
   for k in ('metrics','predictor','multiply','dual','joint','boundary','mem_ipc','load_queue','store_followers'):assert x[k]==original[k],(name,k)
   inputs.append(src/'performance/result.json');tests.append('PASS '+name+' exact accepted RTL and all original counters unchanged')
  else:
   for phase in ('performance','validation'):
    p=src/phase/'result.json';x=read(p);peer=read(src.with_name('load_bp_dual_boundary_'+('mullowtail' if name=='multail' else 'multail'))/phase/'result.json');assert x['status']=='PASS'
    for k in ('metrics','predictor','multiply','dual','joint','boundary','mem_ipc','load_queue','store_followers','mul_tail','pair_reject','pair_supply','pair_census','pair_expand'):assert x[k]==peer[k],(phase,k)
    inputs.append(p)
   p=src/'mul_unit/result.json';assert read(p)['status']=='PASS' and read(p)['cycles']==90000;inputs.append(p);tests.append('PASS '+name+' independent90000-cycle all4op product/control model; fixed1/10 statistics equal peer')
  gen=ROOT/('tools/generate_dual_pair_probe.py' if name=='pairprobe' else 'tools/generate_dual_mul_tail.py');s=gen.read_text();pattern="out=src.with_name('load_bp_dual_boundary_pairprobe')" if name=='pairprobe' else "out=src.with_name('load_bp_'+a.variant)";assert s.count(pattern)==1;target=out/name;s=s.replace(pattern,'out=Path('+repr(str(target))+')');ns={'__file__':str(gen),'__name__':'tail_reproduce'};exec(compile(s,str(gen),'exec'),ns);sys.argv=[str(gen),'--variant','dual_boundary_'+name]
  with (out/(name+'.log')).open('w') as log,contextlib.redirect_stdout(log):ns['main']()
  assert g['override_sha256']==read(target/'generation.json')['override_sha256']
  for p in (src/'ipcore').rglob('*'):
   if p.is_file() and p.suffix in ('.v','.idf'):assert sha(p)==sha(target/'ipcore'/p.relative_to(src/'ipcore'))
  inputs +=[gen,src/'generation.json',target/'generation.json'];tests.append('PASS '+name+' exact source/PLL/RAM regeneration')
 # The producer comparisons and operand storage are unchanged; the new
 # earlier W schedule has also been tested by real core/SoC future-tag checks.
 p=ROOT/'simulation/results/load_bp_dual_boundary_slots/operand_checks/result.json';assert read(p)['status']=='PASS' and read(p)['cycles']==300000;assert sha(ref/'nc_operands.v')==sha(p.parent.parent/'nc_operands.v');inputs.append(p);tests.append('PASS unchanged operand module exact accepted hash reuses independent300000-cycle equivalence')
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print('MUL trial evidence and reconstruction PASS')
if __name__=='__main__':main()
