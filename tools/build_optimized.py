"""Rebuild the active optimization baseline from RTL and verify board STA."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
from verify_board_pnr import inspect
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--verify-only',action='store_true');p.add_argument('--rtl-only',action='store_true',help='Use preserved RTL baseline firmware instead of the accepted compiler profile');p.add_argument('--pds-home',type=Path,default=Path('E:/pango/PDS_2022.2-SP1-Lite'));a=p.parse_args()
 baseline=ROOT/'docs/active_optimization_baseline.json';m=json.loads(baseline.read_text())
 compiler=ROOT/'docs/active_compiler_profile.json'
 if compiler.exists() and not a.rtl_only:
  profile=json.loads(compiler.read_text());assert profile['status']=='ACCEPTED_COMPILER_PROFILE'
  assert profile['compatible_rtl_manifest_sha256']==hashlib.sha256(baseline.read_bytes()).hexdigest(),'Compiler profile requires revalidation against changed RTL baseline'
  for n,h in m['input_sha256'].items():assert hashlib.sha256((ROOT/m['project_directory']/n).read_bytes()).hexdigest()==h,n
  m=profile['hardware']
 project=ROOT/m['project_directory']
 def verify_inputs():
  for name,h in m['input_sha256'].items():assert hashlib.sha256((project/name).read_bytes()).hexdigest()==h,name
 verify_inputs()
 s=(project/'new_core.pds').read_text()
 assert 'constraints/board.fdc' in s and 'input_place_db_file' not in s
 for key,value in [('gplace_seed',m['place_seed']),('groute_seed',m['route_seed'])]:
  found=re.search(r'\(_option '+key+r' \(_integer (\d+)\)\)',s);assert int(found[1])==value
 for key,value in m.get('implementation_options',{}).items():
  assert f'(_option {key} (_integer {value}))' in s,key
 if m.get('priority_routing'):
  for option in ('enable_route_constraint_iterate (_switch ON)','route_constraint_iterate_times (_integer 4)','route_constraint_slack (_real 0.05)','route_constraint_max_timing_path (_integer 5)'):assert '(_option '+option+')' in s,option
 if not a.verify_only:
  s=re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',s)
  (project/'new_core.pds').write_text(s)
  with (project/'verified_rebuild.log').open('wb') as f:
   subprocess.run([str(a.pds_home/'bin/pds_shell.exe'),'-project','new_core.pds','-run','report_timing'],cwd=project,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=3600)
 result=inspect(project,m['configured_cpu_hz']/1000000);verify_inputs()
 (project/'verified_build.json').write_text(json.dumps(result,indent=2)+'\n')
 print('PASS active optimization inputs, actual board pins and all-corner STA',result['estimated_fmax_mhz'])
if __name__=='__main__':main()
