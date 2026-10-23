"""Main project build: source hashes, full STA, then SRAM bitstream."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
from verify_board_pnr import inspect
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def find_pds(explicit=None):
 candidates=[]
 if explicit:candidates.append(Path(explicit)/'bin/pds_shell.exe')
 if os.environ.get('PDS_HOME'):candidates.append(Path(os.environ['PDS_HOME'])/'bin/pds_shell.exe')
 if shutil.which('pds_shell.exe'):candidates.append(Path(shutil.which('pds_shell.exe')))
 for drive in 'CDEFG':
  for folder in ('pango','Pango','Program Files/Pango','Program Files (x86)/Pango',''):
   base=Path(f'{drive}:/')/folder
   if base.exists():candidates.extend(sorted(base.glob('PDS_*/bin/pds_shell.exe'),reverse=True))
 for p in candidates:
  if p.is_file():return p
 raise RuntimeError('PDS not found. Open hardware/pds/new_core.pds in installed PDS, or pass --pds-home.')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--project',type=Path,default=ROOT/'hardware/pds');ap.add_argument('--pds-home');ap.add_argument('--verify-only',action='store_true');a=ap.parse_args()
 project=a.project.resolve();m=json.loads((project/'main_manifest.json').read_text())
 def inputs():
  for n,h in m['input_sha256'].items():assert sha(project/n)==h,n
 inputs();s=(project/'new_core.pds').read_text()
 for key,value in [('gplace_seed',m['place_seed']),('groute_seed',m['route_seed']),('fanout_guide',m['fanout_guide']),('max_ctrl_chain_length',4)]:assert f'(_option {key} (_integer {value}))' in s,key
 for key in ('optimize_multi_corner_timing','fix_hold_violation'):assert f'(_option {key} (_switch ON))' in s,key
 if m.get('priority_routing'):
  for option in ('enable_route_constraint_iterate (_switch ON)','route_constraint_iterate_times (_integer 4)','route_constraint_slack (_real 0.05)','route_constraint_max_timing_path (_integer 5)'):assert '(_option '+option+')' in s,option
 if a.verify_only:
  result=json.loads((project/'release_result.json').read_text())
  assert sha(project/'download/top.sbit')==result['bitstream_sha256']
  assert sha(project/'report_timing/top.rtr')==result['sta_sha256']
  print('PASS main inputs and bitstream hashes');return
 pds=find_pds(a.pds_home)
 (project/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',s))
 with (project/'portable_build.log').open('wb') as log:subprocess.run([str(pds),'-project','new_core.pds','-run','report_timing'],cwd=project,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=3600)
 log=(project/'portable_build.log').read_text(errors='replace');assert 'Process "Report Timing" done.' in log and not re.search(r'^E:',log,re.M)
 result=inspect(project,83);inputs()
 with (project/'bitstream_build.log').open('wb') as log:subprocess.run([str(pds),'-f','generate_bitstream.tcl'],cwd=project,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
 assert not re.search(r'^E:',(project/'bitstream_build.log').read_text(errors='replace'),re.M)
 bit=project/'generate_bitstream/top.sbit';assert bit.is_file() and bit.stat().st_size>1000
 (project/'download').mkdir(exist_ok=True);shutil.copyfile(bit,project/'download/top.sbit')
 result.update(configured_cpu_hz=83000000,iterations=5000,bitstream_sha256=sha(bit),bitstream='download/top.sbit',scope='Full native build and bitstream generation; no board programming or physical board performance claim.')
 (project/'release_result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS main83 STA and bitstream',result['estimated_fmax_mhz'],result['bitstream_sha256'],flush=True)
 if project==ROOT/'hardware/pds':
  out=ROOT/'output/board83';out.mkdir(parents=True,exist_ok=True)
  shutil.copyfile(bit,out/'top.sbit');shutil.copyfile(project/'release_result.json',out/'release_result.json')
if __name__=='__main__':main()
