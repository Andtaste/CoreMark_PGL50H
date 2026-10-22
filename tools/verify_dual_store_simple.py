"""Verify equal schedules, unchanged boundaries and exact regeneration."""
from pathlib import Path
import contextlib,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 out=ROOT/'simulation/results/dual_store_simple_verify';out.mkdir(exist_ok=False);ref=ROOT/'simulation/results/load_bp_dual_boundary_storeack';accepted=ROOT/'docs/accepted_dual_baseline.json';assert read(accepted)['variant']=='dual_boundary_slots';tests=[];inputs=[Path(__file__).resolve(),accepted]
 for v in ('dual_boundary_storewrite','dual_boundary_storelogic'):
  src=ROOT/('simulation/results/load_bp_'+v)
  for phase in ('performance','validation'):
   x=read(src/phase/'result.json');r=read(ref/phase/'result.json');assert x['status']==r['status']=='PASS'
   for k in ('metrics','predictor','multiply','dual','joint','boundary','mem_ipc','load_queue','store_followers'):assert x[k]==r[k],(v,phase,k)
   inputs +=[src/phase/'result.json',ref/phase/'result.json'];tests.append('PASS '+v+' '+phase+' every measured counter unchanged')
  for n in ('nc_core.v','nc_soc.v','nc_operands.v','nc_regfile.v','nc_fetch.v','nc_execute.v','nc_mul_pipeline.v','nc_btb.v','nc_csr.v','nc_stats.v','top.v'):
   assert sha(src/n)==sha(ref/n);inputs +=[src/n,ref/n]
  if v.endswith('storewrite'):assert sha(src/'nc_memory.v')==sha(ref/'nc_memory.v')
  proof=src/'simple_proof/result.json';assert read(proof)['status']=='PASS';inputs.append(proof)
  gen=ROOT/'tools/generate_dual_store_simple.py';s=gen.read_text();pattern="out=src.with_name('load_bp_'+a.variant)";assert s.count(pattern)==1;target=out/v;s=s.replace(pattern,'out=Path('+repr(str(target))+')');ns={'__file__':str(gen),'__name__':'simple_regeneration'};exec(compile(s,str(gen),'exec'),ns);sys.argv=[str(gen),'--variant',v]
  with (out/(v+'.log')).open('w') as log,contextlib.redirect_stdout(log):ns['main']()
  assert read(src/'generation.json')['override_sha256']==read(target/'generation.json')['override_sha256']
  for p in (src/'ipcore').rglob('*'):
   if p.is_file() and p.suffix in ('.v','.idf'):assert sha(p)==sha(target/'ipcore'/p.relative_to(src/'ipcore'))
  inputs +=[gen,src/'generation.json',target/'generation.json'];tests.append('PASS '+v+' generated RTL/PLL/RAM exact reconstruction; core, operand boundaries and execution sources unchanged')
 ev=ROOT/'simulation/results/load_bp_dual_boundary_slots/operand_checks/result.json';assert read(ev)['status']=='PASS' and read(ev)['cycles']==300000;inputs.append(ev);tests.append('PASS unchanged accepted operand module reuses its independent 300000-cycle equivalence')
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print('schedule, boundaries and regeneration PASS')
if __name__=='__main__':main()
