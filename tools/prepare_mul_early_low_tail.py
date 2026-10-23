"""Try ordered MEM consumption of the short pipeline's low completion before table write."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'simulation/results/autonomous_20261022'

def main():
 manifest=ROOT/'docs/active_optimization_baseline.json'
 m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 assert m['source_trial']=='mul_early_products'
 for name,digest in m['input_sha256'].items():
  assert hashlib.sha256((src/name).read_bytes()).hexdigest()==digest,name
 dest=WORK/'mul_early_low_tail';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):
  shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(manifest,dest/'parent_baseline.json')
 p=dest/'source/core/nc_mul_pipeline.v';s=p.read_text()
 old=' assign query_ready=available[query_tag];assign query_data=results[query_tag];';assert s.count(old)==1
 s=s.replace(old,''' // Only the ordered MEM owner can consume a completing low result.
 // Producer broadcasts remain registered; readiness does not feed selection.
 wire query_low=low_done && tag1==query_tag;
 assign query_ready=available[query_tag] || query_low;
 assign query_data=query_low ? low_completed : results[query_tag];''')
 for tag,done in [('tag1','low_done'),('tag2','high_done')]:
  old=f'   if({done}) available[{tag}]<=1;';assert s.count(old)==1
  s=s.replace(old,f'   if({done} && !(consume && query_tag=={tag})) available[{tag}]<=1;')
 p.write_text(s)
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=m['source_trial'],intent='Low-result terminal bypass into ordered MEM; consume wins availability on simultaneous completion; registered forwarding unchanged'),indent=2)+'\n')
 print('PREPARED',dest.name)

if __name__=='__main__':main()
