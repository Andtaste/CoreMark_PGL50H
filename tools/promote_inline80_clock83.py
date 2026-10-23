"""Reproduce the passing seed, then adopt with the previous82MHz profile preserved."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess
from verify_board_pnr import inspect
ROOT=Path(__file__).resolve().parents[1]
TRIAL=ROOT/'simulation/results/continuous_clock83_inline80_fanout64_p7r2_20261022'
PROJECT=ROOT/'hardware/pds_optimized_inline80_clock83_20261023'
ACTIVE=ROOT/'docs/active_compiler_profile.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['build','adopt']);a=ap.parse_args()
 old=json.loads(ACTIVE.read_text())
 assert old==json.loads((TRIAL/'parent_compiler_profile.json').read_text())
 for n,h in old['hardware']['input_sha256'].items():assert sha(ROOT/old['hardware']['project_directory']/n)==h,n
 for n,h in json.loads((TRIAL/'prepared.json').read_text())['input_sha256'].items():assert sha(TRIAL/n)==h,n
 first=inspect(TRIAL,83)
 if a.action=='build':
  assert not PROJECT.exists();PROJECT.mkdir()
  for folder in ('source','ipcore','constraints','memory'):shutil.copytree(TRIAL/folder,PROJECT/folder)
  for p in (PROJECT/'ipcore').rglob('*'):
   if p.is_file() and p.suffix in ('.v','.idf','.vhdl'):p.write_bytes(p.read_bytes().replace(TRIAL.as_posix().encode(),PROJECT.as_posix().encode()))
  s=re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(TRIAL/'new_core.pds').read_text());(PROJECT/'new_core.pds').write_text(s)
  shutil.copyfile(ACTIVE,PROJECT/'parent_compiler_profile.json')
  with (PROJECT/'independent_build.log').open('wb') as f:subprocess.run(['E:/pango/PDS_2022.2-SP1-Lite/bin/pds_shell.exe','-project','new_core.pds','-run','report_timing'],cwd=PROJECT,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=3600)
  log=(PROJECT/'independent_build.log').read_text(errors='replace');assert 'Process "Report Timing" done.' in log and not re.search(r'^E:',log,re.M)
  save(PROJECT/'verified_build.json',inspect(PROJECT,83));print('INDEPENDENT83 PASS',flush=True);return
 second=inspect(PROJECT,83)
 for k in ('estimated_fmax_mhz','corners','routed_resources'):assert first[k]==second[k],k
 inputs={}
 for folder in ('source','ipcore','constraints','memory'):
  for p in (PROJECT/folder).rglob('*'):
   if p.is_file():
    n=str(p.relative_to(PROJECT));assert p.read_bytes().replace(PROJECT.as_posix().encode(),TRIAL.as_posix().encode())==(TRIAL/n).read_bytes(),n;inputs[n]=sha(p)
 baseline=ROOT/'docs/active_optimization_baseline.json';assert old['compatible_rtl_manifest_sha256']==sha(baseline)
 backup=ROOT/'docs/compiler_profile_clock82_preserved.json';assert not backup.exists();shutil.copyfile(ACTIVE,backup)
 old['hardware']=dict(project_directory=str(PROJECT.relative_to(ROOT)),configured_cpu_hz=83000000,place_seed=7,route_seed=2,implementation_options={'fanout_guide':64},input_sha256=inputs,estimated_fmax_mhz=second['estimated_fmax_mhz'],resources=second['routed_resources'],physical_verification=second,independent_native_runs=2)
 old['clock_adoption']=dict(previous_profile=str(backup.relative_to(ROOT)),throughput_gain_pct=100*(83/82-1),minimum_setup_slack_ns=.013,decision='ACCEPT: two independent complete native runs pass all corners and board pins; throughput priority. Tight13ps margin explicitly retained; original82MHz project remains available.',sweep=str((TRIAL.parent/'continuous_clock83_inline80_sweep_20261022/sweep_results.json').relative_to(ROOT)))
 for p in [TRIAL.parent/'continuous_clock83_inline80_sweep_checks/inline80_result.json',TRIAL.parent/'continuous_clock83_inline80_sweep_io/result.json']:
  assert json.loads(p.read_text())['status']=='PASS';old['evidence_sha256'][str(p.relative_to(ROOT))]=sha(p)
 old['scope']='Current actual83MHz fanout64 seed7/2 hardware and5000-iteration inline80 ROM independently built twice. At83MHz, fixed historical1/10 and current inline80 10-iteration CRC/counters pass; vendorRAM andUART720 pass. Existing100-iteration compiler comparison was measured at82MHz. Clock throughput gain83/82 is projected from unchanged cycles, not a measured board score. No board programming.'
 save(PROJECT/'clock_adoption.json',old);save(ACTIVE,old);print('ADOPTED83',second['estimated_fmax_mhz'],flush=True)
if __name__=='__main__':main()
