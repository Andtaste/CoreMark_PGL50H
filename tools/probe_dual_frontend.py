"""Simulation-only control: wide frontend but pair issuance forced off."""
from pathlib import Path
import hashlib,json,shutil,sys
import research_dual_issue as trial
def main():
 original=trial.OUT;dest=original.with_name('load_bp_dual_frontend_only');dest.mkdir(exist_ok=True)
 meta=json.loads((original/'generation.json').read_text())
 for n,h in meta['override_sha256'].items():
  src=original/Path(n).name;assert trial.sha(src)==h,n;shutil.copyfile(src,dest/src.name)
 core=dest/'nc_core.v';s=core.read_text();old='wire pair_candidate=id_second';assert s.count(old)==1
 core.write_text(s.replace(old,"wire pair_candidate=1'b0 && id_second"))
 for n in meta['override_sha256']:
  meta['override_sha256'][n]=trial.sha(dest/Path(n).name)
 meta['probe']='Same wide frontend, pair_candidate forced false; simulation only'
 (dest/'generation.json').write_text(json.dumps(meta,indent=2)+'\n')
 trial.OUT=dest;sys.argv=[sys.argv[0],'--phase','performance'];trial.main()
 for path in (dest/'result.json',dest/'performance/result.json'):
  r=json.loads(path.read_text());r['variant']='dual_frontend_only';r['scope']=meta['probe'];r['input_sha256'][str(Path(__file__).resolve().relative_to(trial.ROOT))]=trial.sha(Path(__file__))
  path.write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
