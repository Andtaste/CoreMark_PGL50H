"""Vary BTB index folding without changing capacity, tags or training."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'simulation/results/autonomous_20261022'
def main():
 manifest=ROOT/'docs/active_optimization_baseline.json';m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 for n,h in m['input_sha256'].items():assert hashlib.sha256((src/n).read_bytes()).hexdigest()==h,n
 for offset in (9,10):
  dest=WORK/f'btb_fold{offset}';assert not dest.exists();dest.mkdir()
  for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
  (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
  shutil.copyfile(manifest,dest/'parent_baseline.json')
  p=dest/'source/core/nc_btb.v';s=p.read_text()
  for pc in ('lookup_pc','update_pc'):
   old=f'{pc}[7:3]^{pc}[12:8]';assert s.count(old)==1;s=s.replace(old,f'{pc}[7:3]^{pc}[{offset+4}:{offset}]')
  p.write_text(s)
  (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
  print('PREPARED',dest.name)
if __name__=='__main__':main()
