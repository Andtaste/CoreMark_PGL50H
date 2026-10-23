"""Avoid grouping a slow primary with a side instruction waiting on an older producer."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'simulation/results/autonomous_20261022'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 manifest=ROOT/'docs/active_optimization_baseline.json';m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 for n,h in m['input_sha256'].items():assert sha(src/n)==h,n
 for name,condition in [('mul_split','id_kind==6'),('slow_split','(id_kind==4 || id_kind==6)')]:
  dest=WORK/name;assert not dest.exists();dest.mkdir()
  for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
  (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
  shutil.copyfile(manifest,dest/'parent_baseline.json')
  p=dest/'source/core/nc_core.v';s=p.read_text();old='wire pair_candidate=id_second && !id_fault && id_pair_flags[4] &&'
  assert s.count(old)==1;s=s.replace(old,'// Declining a pair leaves its second instruction at the fetch head.\n wire pair_candidate=!('+condition+' && (dep_c || dep_d)) && id_second && !id_fault && id_pair_flags[4] &&');p.write_text(s)
  (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):sha(p) for p in dest.rglob('*') if p.is_file()},indent=2)+'\n');print('PREPARED',name)
if __name__=='__main__':main()
