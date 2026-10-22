"""Freeze exact head-local reconstruction, schedules, and pointer FF evidence."""
from pathlib import Path
import contextlib,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 out=ROOT/'simulation/results/dual_head_local_verify';out.mkdir(exist_ok=False);accepted=ROOT/'docs/accepted_dual_baseline.json';a=read(accepted);assert a['variant']=='dual_boundary_storewrite';ref=ROOT/a['source_directory'];src=ROOT/'simulation/results/load_bp_dual_boundary_headlocal';g=read(src/'generation.json');assert g['accepted_dual_sha256']==sha(accepted);inputs=[Path(__file__).resolve(),accepted];tests=[];changed=[]
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;inputs.append(p)
  if sha(ref/p.name)!=h:changed.append(p.name)
 assert changed==['nc_operands.v']
 for phase in ('performance','validation'):
  p=src/phase/'result.json';r=ref/phase/'result.json';x=read(p);y=read(r);assert x['status']==y['status']=='PASS'
  for key in ('metrics','predictor','multiply','dual','joint','boundary','mem_ipc','load_queue','store_followers'):assert x[key]==y[key],(phase,key)
  inputs +=[p,r];tests.append('PASS '+phase+' all original counters identical')
 for sub in ('forward_equivalence','integration_run'):
  p=src/sub/'result.json';assert read(p)['status']=='PASS';inputs.append(p)
 gen=ROOT/'tools/generate_dual_head_local.py';assert sha(gen)==g['generator_sha256'];s=gen.read_text();pattern="out=src.with_name('load_bp_dual_boundary_headlocal')";assert s.count(pattern)==1;target=out/'reproduced';s=s.replace(pattern,'out=Path('+repr(str(target))+')');ns={'__file__':str(gen),'__name__':'head_local_reproduction'};exec(compile(s,str(gen),'exec'),ns)
 with (out/'reproduction.log').open('w') as log,contextlib.redirect_stdout(log):ns['main']()
 assert g['override_sha256']==read(target/'generation.json')['override_sha256']
 for p in (src/'ipcore').rglob('*'):
  if p.is_file() and p.suffix in ('.v','.idf'):assert sha(p)==sha(target/'ipcore'/p.relative_to(src/'ipcore'))
 inputs +=[gen,src/'generation.json',target/'generation.json'];tests.append('PASS only operand head pointer copies changed; exact RTL/PLL/RAM regeneration')
 net=src/'pds/synthesize/top_syn.vm';text=net.read_text(errors='replace');names=re.findall(r'GTP_DFF\w*\s*/\*\s*(?:\\)?local_rd\[(\d+)\]\s*\*/',text)
 assert set(names)==set(map(str,range(6))),(names,'pointer copies not physically retained')
 inputs.append(net);tests.append('PASS post-synthesis GTP_DFF nodes retain all six local_rd pointer bits; full sequential module equivalence proves same-edge state behavior')
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,retained_pointer_bits=names,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print('Head local exact counters/reconstruction/pointer FF verification PASS')
if __name__=='__main__':main()
