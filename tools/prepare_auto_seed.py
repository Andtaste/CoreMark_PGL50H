"""Create an isolated native placement trial without changing RTL or firmware."""
from pathlib import Path
import argparse, hashlib, json, re, shutil, subprocess
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'simulation/results/autonomous_20261022'

def main():
 p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--place',type=int,required=True);p.add_argument('--route',type=int,default=1);p.add_argument('--run',action='store_true');a=p.parse_args()
 assert re.fullmatch('[a-z0-9_]+',a.name)
 src=WORK/a.name;dest=WORK/f'{a.name}_p{a.place}r{a.route}';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
 s=(src/'new_core.pds').read_text();s=re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',s)
 for key,value in [('gplace_seed',a.place),('groute_seed',a.route)]:
  s,n=re.subn(r'\(_option '+key+r' \(_integer \d+\)\)',f'(_option {key} (_integer {value}))',s);assert n==1
 assert 'input_place_db_file' not in s
 (dest/'new_core.pds').write_text(s)
 shutil.copyfile(src/'parent_baseline.json',dest/'parent_baseline.json')
 hashes={str(f.relative_to(dest)):hashlib.sha256(f.read_bytes()).hexdigest() for folder in ('source','ipcore','constraints','memory') for f in (dest/folder).rglob('*') if f.is_file()}
 for n,h in hashes.items():assert hashlib.sha256((src/n).read_bytes()).hexdigest()==h,n
 (dest/'inputs.json').write_text(json.dumps(hashes,indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=a.name,place_seed=a.place,route_seed=a.route,identical_inputs=True),indent=2)+'\n')
 print('PREPARED',dest,flush=True)
 if a.run:
  with (dest/'native_build.log').open('wb') as f:subprocess.run(['E:/pango/PDS_2022.2-SP1-Lite/bin/pds_shell.exe','-project','new_core.pds','-run','report_timing'],cwd=dest,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=3600)

if __name__=='__main__':main()
