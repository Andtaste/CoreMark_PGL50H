"""Evaluate unconditional primary multiply splitting with registered classification."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'simulation/results/autonomous_20261022'
def main():
 src=WORK/'mul_predecode';dest=WORK/'mul_nopair';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(src/'parent_baseline.json',dest/'parent_baseline.json')
 p=dest/'source/core/nc_core.v';s=p.read_text();old='wire pair_candidate=!(id_mul_hint && (dep_c || dep_d))';assert s.count(old)==1;p.write_text(s.replace(old,'wire pair_candidate=!id_mul_hint'))
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial='mul_predecode',intent='Primary multiply always issues alone; simplify pair admission'),indent=2)+'\n')
 print('PREPARED mul_nopair')
if __name__=='__main__':main()
