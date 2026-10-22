"""Check unchanged statistics and regenerate the final isolated RTL exactly."""
from pathlib import Path
import contextlib,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 out=ROOT/'simulation/results/dual_store_prefix_verify';out.mkdir(exist_ok=False)
 src=ROOT/'simulation/results/load_bp_dual_boundary_storeprefix';inputs=[Path(__file__).resolve()];tests=[]
 for phase in ('performance','validation'):
  z=read(src/phase/'result.json');assert z['status']=='PASS';inputs.append(src/phase/'result.json')
  for suffix in ('storeack','storemmio'):
   p=src.with_name('load_bp_dual_boundary_'+suffix)/phase/'result.json';x=read(p);inputs.append(p)
   for key in ('metrics','predictor','multiply','dual','joint','boundary','mem_ipc','load_queue','store_followers'):assert z[key]==x[key],(phase,suffix,key)
  tests.append('PASS '+phase+' all counters identical across three implementations')
 ref=ROOT/'simulation/results/load_bp_dual_boundary_slots';ev=ref/'operand_checks/result.json';assert read(ev)['status']=='PASS' and read(ev)['cycles']==300000
 for n in ('nc_operands.v','nc_execute.v','nc_mul_pipeline.v','nc_regfile.v','nc_fetch.v','nc_btb.v','nc_csr.v','nc_stats.v'):
  assert sha(ref/n)==sha(src/n);inputs +=[ref/n,src/n]
 inputs.append(ev);tests.append('PASS unchanged operand module exact hash; independent 300000-cycle equivalence evidence remains applicable')
 gen=ROOT/'tools/generate_dual_store_prefix.py';s=gen.read_text();pattern="out=src.with_name('load_bp_dual_boundary_storeprefix')";assert s.count(pattern)==1
 target=out/'reproduced';s=s.replace(pattern,'out=Path('+repr(str(target))+')');ns={'__file__':str(gen),'__name__':'prefix_reproduction'};exec(compile(s,str(gen),'exec'),ns)
 with (out/'reproduction.log').open('w') as log,contextlib.redirect_stdout(log):ns['main']()
 assert read(src/'generation.json')['override_sha256']==read(target/'generation.json')['override_sha256']
 for p in (src/'ipcore').rglob('*'):
  if p.is_file() and p.suffix in ('.v','.idf'):assert sha(p)==sha(target/'ipcore'/p.relative_to(src/'ipcore'))
 inputs +=[gen,src/'generation.json',target/'generation.json'];tests.append('PASS exact generated RTL/PLL/RAM reconstruction')
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print('prefix evidence and regeneration PASS')
if __name__=='__main__':main()
