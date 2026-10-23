"""Capture load return into existing operand registers on the current short-multiply core."""
from pathlib import Path
import hashlib,json,re,shutil,textwrap
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'simulation/results/autonomous_20261022'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,old,new):
 assert s.count(old)==1,(old,s.count(old))
 return s.replace(old,new)

def main():
 manifest=ROOT/'docs/active_optimization_baseline.json'
 m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 assert m['source_trial']=='mul_early_products'
 for name,digest in m['input_sha256'].items():assert sha(src/name)==digest,name
 dest=WORK/'shortmul_loadcapture';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):
  shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(manifest,dest/'parent_baseline.json')
 names={'c':'nc_core.v','o':'nc_operands.v','m':'nc_memory.v','e':'nc_execute.v'}
 context={key:(dest/'source/core'/name).read_text() for key,name in names.items()}
 context['rep']=rep
 transformations=[
  ('generate_dual_next_loadcapture.py'," m=rep(m,'input wire rsp_error);'",' for name,s in '),
 ]
 scripts={}
 for name,start,end in transformations:
  script=ROOT/'tools'/name;code=script.read_text()
  assert code.count(start)==1 and code.count(end)==1,name
  fragment=code[code.index(start):code.index(end)]
  # Execute only the existing checked RTL transformations, not historical
  # directory creation or baseline selection from these archived generators.
  exec(compile(textwrap.dedent(fragment),str(script),'exec'),context)
  scripts[str(script.relative_to(ROOT))]=sha(script)
 for key,name in names.items():(dest/'source/core'/name).write_text(context[key])
 assert sha(dest/'source/core/nc_mul_pipeline.v')==sha(src/'source/core/nc_mul_pipeline.v')
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):sha(p) for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=m['source_trial'],transformation_sha256=scripts,intent='Capture formatted load return into existing operand value registers; no current-cycle return-to-EX path or readiness change. Re-evaluate physical timing on short-multiplier baseline.'),indent=2)+'\n')
 print('PREPARED',dest.name)

if __name__=='__main__':main()
