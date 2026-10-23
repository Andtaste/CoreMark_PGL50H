"""Prepare an isolated ordinary PDS project using identical hardware and firmware."""
from pathlib import Path
import argparse,hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--mhz',type=int,required=True);p.add_argument('--suffix',default='');p.add_argument('--place',type=int,required=True);p.add_argument('--route',type=int,required=True);a=p.parse_args()
 assert not a.suffix or re.fullmatch('[a-z0-9_]+',a.suffix)
 label=str(a.mhz)+('_'+a.suffix if a.suffix else '')
 src=ROOT/f'simulation/results/continuous_clock{label}_20261022';dest=src.parent/f'continuous_clock{label}_p{a.place}r{a.route}_20261022';assert not dest.exists()
 original=json.loads((src/'prepared.json').read_text())
 for n,h in original['input_sha256'].items():assert hashlib.sha256((src/n).read_bytes()).hexdigest()==h,n
 dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
 for path in (dest/'ipcore').rglob('*'):
  if path.is_file() and path.suffix in ('.v','.idf','.vhdl'):
   path.write_bytes(path.read_bytes().replace(src.as_posix().encode(),dest.as_posix().encode()))
 s=(src/'new_core.pds').read_text();s=re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',s)
 for key,value in [('gplace_seed',a.place),('groute_seed',a.route)]:
  s,n=re.subn(r'\(_option '+key+r' \(_integer \d+\)\)',f'(_option {key} (_integer {value}))',s);assert n==1
 (dest/'new_core.pds').write_text(s)
 shutil.copyfile(src/'parent_baseline.json',dest/'parent_baseline.json')
 meta=json.loads((src/'prepared.json').read_text());meta.update(parent_trial=str(src.relative_to(ROOT)),place_seed=a.place,route_seed=a.route)
 meta['input_sha256']={str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('source','ipcore','constraints','memory') for p in (dest/folder).rglob('*') if p.is_file()}
 (dest/'prepared.json').write_text(json.dumps(meta,indent=2)+'\n');print('PREPARED',dest)
if __name__=='__main__':main()
