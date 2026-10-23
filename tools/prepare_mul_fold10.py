"""Combine two measured cycle reductions, then revalidate the whole design."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'simulation/results/autonomous_20261022'
def main():
 src=WORK/'mul_predecode';dest=WORK/'mul_fold10';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(src/'parent_baseline.json',dest/'parent_baseline.json')
 shutil.copyfile(WORK/'btb_fold10/source/core/nc_btb.v',dest/'source/core/nc_btb.v')
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial='mul_predecode',second_trial='btb_fold10',intent='Combine early multiplication issue with reduced BTB conflicts; neither component adopted individually'),indent=2)+'\n')
 print('PREPARED mul_fold10')
if __name__=='__main__':main()
