"""Evaluate whether side dependencies unnecessarily delay primary branches."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'simulation/results/autonomous_20261022'
def main():
 manifest=ROOT/'docs/active_optimization_baseline.json';m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 for n,h in m['input_sha256'].items():assert hashlib.sha256((src/n).read_bytes()).hexdigest()==h,n
 dest=WORK/'branch_side_wait';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(manifest,dest/'parent_baseline.json')
 p=dest/'source/core/nc_core.v';s=p.read_text();old='wire pair_candidate=!(id_mul_hint && (dep_c || dep_d))';assert s.count(old)==1
 s=s.replace(old,'// Among eligible primaries, bit6 selects conditional branches.\n wire pair_candidate=!((id_mul_hint || id_insn[6]) && (dep_c || dep_d))');p.write_text(s)
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=m.get('source_trial'),intent='Allow primary branch resolution without waiting for a dependent side instruction'),indent=2)+'\n')
 print('PREPARED branch_side_wait')
if __name__=='__main__':main()
