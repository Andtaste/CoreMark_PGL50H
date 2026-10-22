"""Preserve initial generator bytes and reproduce all trial RTL in fresh folders."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 source=ROOT/'tools/generate_dual_resource_trials.py';s=source.read_text()
 old=s.replace("('resourceside','resourcequeue','resourceboth','resourcecompare')","('resourceside','resourcequeue','resourceboth')")
 start=old.index(" if a.trial=='resourcecompare':");end=old.index(" for n in g['override_sha256']:",start);old=old[:start]+old[end:]
 out=ROOT/'simulation/results/dual_resource_reproduction';out.mkdir(exist_ok=True)
 historical=out/'generate_pc_v1.py';historical.write_bytes(old.encode('utf-8'))
 expected=json.loads((ROOT/'simulation/results/load_bp_dual_boundary_next_resourceside/generation.json').read_text())['generator_sha256'];assert sha(historical)==expected,(sha(historical),expected)
 descriptor=ROOT/'docs/accepted_dual_baseline.json';guard=sha(descriptor);records=[]
 import sys
 for t in ('resourceside','resourcequeue','resourceboth','resourcecompare'):
  gen=historical if t!='resourcecompare' else source;code=gen.read_text()
  code=code.replace("dest=src.with_name('load_bp_dual_boundary_next_'+a.trial)","dest=ROOT/('simulation/results/dual_resource_reproduction/'+a.trial)")
  sys.argv=[str(gen),'--trial',t];ns={'__file__':str(gen),'__name__':'reproduction'};exec(compile(code,str(gen),'exec'),ns);ns['ROOT']=ROOT;ns['main']()
  actual=ROOT/('simulation/results/load_bp_dual_boundary_next_'+t);copy=out/t;g=json.loads((actual/'generation.json').read_text());assert sha(gen)==g['generator_sha256']
  files=[p for p in copy.rglob('*') if p.is_file() and p.name!='generation.json']
  for p in files:assert sha(p)==sha(actual/p.relative_to(copy)),p
  records.append(dict(trial=t,files=len(files),generator_sha256=sha(gen),source_sha256={str(p.relative_to(copy)):sha(p) for p in files}))
 assert sha(descriptor)==guard
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=records,accepted_descriptor_sha256=guard,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in [source,historical,Path(__file__).resolve()]}),indent=2)+'\n');print('PASS reproduced four resource variants')
if __name__=='__main__':main()
