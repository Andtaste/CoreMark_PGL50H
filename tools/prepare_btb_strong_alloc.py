"""Evaluate strongly initialized per-context counters at unchanged BTB capacity."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
def main():
 manifest=ROOT/'docs/active_optimization_baseline.json'
 m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 for n,h in m['input_sha256'].items():assert hashlib.sha256((src/n).read_bytes()).hexdigest()==h,n
 dest=ROOT/'simulation/results/autonomous_20261022/btb_strong_alloc';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(manifest,dest/'parent_baseline.json')
 p=dest/'source/core/nc_btb.v';s=p.read_text();old="{update_taken,{2{update_taken ? 2'b10 : 2'b01}}}"
 assert s.count(old)==1;p.write_text(s.replace(old,"{5{update_taken}}"))
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=m['source_trial'],intent='Initialize both local-history counters strongly toward observed allocation outcome; retain full tags, capacity, hash, update timing and saturation transitions.'),indent=2)+'\n')
 print('PREPARED',dest.name)
if __name__=='__main__':main()
