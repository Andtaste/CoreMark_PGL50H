"""Single-option implementation trials on validated actual-83MHz inputs."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('strategy',choices=['slack99','refine40','compact0','fanout64']);ap.add_argument('--run',action='store_true');a=ap.parse_args()
 src=ROOT/'simulation/results/continuous_clock83_shortmul_20261022'
 meta=json.loads((src/'prepared.json').read_text())
 assert json.loads((src/'parent_baseline.json').read_text())==json.loads((ROOT/'docs/active_optimization_baseline.json').read_text())
 for n,h in meta['input_sha256'].items():assert sha(src/n)==h,n
 dest=src.parent/f'continuous_clock83_shortmul_{a.strategy}_20261022';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
 for p in (dest/'ipcore').rglob('*'):
  if p.is_file() and p.suffix in ('.v','.idf','.vhdl'):
   p.write_bytes(p.read_bytes().replace(src.as_posix().encode(),dest.as_posix().encode()))
 for folder in ('source','ipcore','constraints','memory'):
  for p in (dest/folder).rglob('*'):
   if p.is_file():assert p.read_bytes().replace(dest.as_posix().encode(),src.as_posix().encode())==(src/p.relative_to(dest)).read_bytes(),p
 s=(src/'new_core.pds').read_text();s=re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',s)
 key,value={'slack99':('slack_weight',99),'refine40':('refineplacement_iteration',40),'compact0':('plc_decongestion',0),'fanout64':('fanout_guide',64)}[a.strategy]
 assert f'(_option {key} ' not in s
 needle='(_option selected_syn_tool_opt (_integer 2))' if a.strategy=='fanout64' else '(_option gplace_seed (_integer 3))';assert s.count(needle)==1
 s=s.replace(needle,needle+f'\n            (_option {key} (_integer {value}))')
 (dest/'new_core.pds').write_text(s);shutil.copyfile(src/'parent_baseline.json',dest/'parent_baseline.json')
 meta.update(parent_trial=str(src.relative_to(ROOT)),strategy=a.strategy,changed_option={key:value},changed_stage='synthesize' if a.strategy=='fanout64' else 'pnr',place_seed=3,route_seed=1,scope='One implementation option only; source/IP/firmware/constraints identical after local path normalization. Reuse base83 fixed-image, rebuilt-metadata, UART and vendor-RAM functional checks. Software compiler flags unchanged.')
 meta['input_sha256']={str(p.relative_to(dest)):sha(p) for folder in ('source','ipcore','constraints','memory') for p in (dest/folder).rglob('*') if p.is_file()}
 meta['project_sha256_before_build']=sha(dest/'new_core.pds')
 (dest/'prepared.json').write_text(json.dumps(meta,indent=2)+'\n')
 print('PREPARED',dest,flush=True)
 if a.run:
  with (dest/'native_build.log').open('wb') as f:subprocess.run(['E:/pango/PDS_2022.2-SP1-Lite/bin/pds_shell.exe','-project','new_core.pds','-run','report_timing'],cwd=dest,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=3600)
if __name__=='__main__':main()
