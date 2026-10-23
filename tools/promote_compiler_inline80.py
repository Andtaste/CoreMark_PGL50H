"""Independently rebuild and compose a software profile with the accepted RTL."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess
from verify_board_pnr import inspect
ROOT=Path(__file__).resolve().parents[1]
TRIAL=ROOT/'simulation/results/continuous_clock82_shortmul_o3_inline80_20261022'
PROJECT=ROOT/'hardware/pds_optimized_inline80_20261023'
OUT=ROOT/'simulation/results/compiler_profiles_20261023'
ACTIVE=ROOT/'docs/active_optimization_baseline.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['build','adopt']);args=ap.parse_args()
 parent=json.loads(ACTIVE.read_text());assert parent==json.loads((TRIAL/'parent_baseline.json').read_text())
 for n,h in parent['input_sha256'].items():assert sha(ROOT/parent['project_directory']/n)==h,n
 for n,h in json.loads((TRIAL/'prepared.json').read_text())['input_sha256'].items():assert sha(TRIAL/n)==h,n
 first=inspect(TRIAL,82)
 if args.action=='build':
  assert not PROJECT.exists();PROJECT.mkdir()
  for folder in ('source','ipcore','constraints','memory'):shutil.copytree(TRIAL/folder,PROJECT/folder)
  for p in (PROJECT/'ipcore').rglob('*'):
   if p.is_file() and p.suffix in ('.v','.idf','.vhdl'):p.write_bytes(p.read_bytes().replace(TRIAL.as_posix().encode(),PROJECT.as_posix().encode()))
  s=re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(TRIAL/'new_core.pds').read_text());(PROJECT/'new_core.pds').write_text(s)
  shutil.copyfile(ACTIVE,PROJECT/'parent_baseline.json')
  with (PROJECT/'independent_build.log').open('wb') as f:subprocess.run(['E:/pango/PDS_2022.2-SP1-Lite/bin/pds_shell.exe','-project','new_core.pds','-run','report_timing'],cwd=PROJECT,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=3600)
  save(PROJECT/'verified_build.json',inspect(PROJECT,82));print('INDEPENDENT INLINE80 BUILD PASS',flush=True);return
 second=inspect(PROJECT,82)
 assert 'Process "Report Timing" done.' in (PROJECT/'independent_build.log').read_text(errors='replace')
 for k in ('estimated_fmax_mhz','corners','routed_resources'):assert first[k]==second[k],k
 inputs={}
 for folder in ('source','ipcore','constraints','memory'):
  for p in (PROJECT/folder).rglob('*'):
   if p.is_file():
    n=str(p.relative_to(PROJECT));assert p.read_bytes().replace(PROJECT.as_posix().encode(),TRIAL.as_posix().encode())==(TRIAL/n).read_bytes(),n;inputs[n]=sha(p)
 evidence={}
 for path in [OUT/'result.json',OUT/'extra_result.json',OUT/'o3_inline80_10.json',OUT/'o3_inline80_validation.json',OUT/'o3_inline80_100.json',OUT/'longer_comparison.json',OUT/'reproducible_cli.json',OUT/'inline80_repeat.json',ROOT/'simulation/results/continuous_clock82_shortmul_o3_inline80_io/result.json']:
  data=json.loads(path.read_text());assert data['status']=='PASS',path;evidence[str(path.relative_to(ROOT))]=sha(path)
 fixed=json.loads((OUT/'o3_inline80_10.json').read_text());long=json.loads((OUT/'o3_inline80_100.json').read_text());base=json.loads((OUT/'baseline_10.json').read_text());base100=json.loads((OUT/'longer_comparison.json').read_text())['runs'][0]
 assert fixed['cycles']<base['cycles'] and long['cycles']<base100['cycles']
 assert sha(PROJECT/'memory/boot.hex')==json.loads((OUT/'reproducible_cli.json').read_text())['image_sha256']
 hardware=dict(project_directory=str(PROJECT.relative_to(ROOT)),configured_cpu_hz=82000000,place_seed=3,route_seed=1,input_sha256=inputs,estimated_fmax_mhz=second['estimated_fmax_mhz'],resources=second['routed_resources'],physical_verification=second,independent_native_runs=2)
 record=dict(status='ACCEPTED_COMPILER_PROFILE',profile='o3_inline80',added_flags=['-O3','--param=max-inline-insns-auto=80'],source_date_epoch=1792684800,compatible_rtl_manifest_sha256=sha(ACTIVE),rtl_baseline=str(ACTIVE.relative_to(ROOT)),hardware=hardware,firmware_bytes=54260,firmware_iterations=5000,diagnostic_10=dict(cycles=fixed['cycles'],baseline_cycles=base['cycles'],cm_per_mhz=10e6/fixed['cycles'],gain_pct=100*(base['cycles']/fixed['cycles']-1)),diagnostic_100=dict(cycles=long['cycles'],baseline_cycles=base100['cycles'],cm_per_mhz=100e6/long['cycles'],gain_pct=100*(base100['cycles']/long['cycles']-1)),evidence_sha256=evidence,scope='Compiler gains compare freshly built identical-source baseline at the same iteration count. RTL baseline fixed historical-image metrics remain separate. Actual82MHz hardware and5000-iteration ROM built twice; firmware performance tested at1/10/100 iterations. No board programming or official board CoreMark score.')
 target=ROOT/'docs/active_compiler_profile.json';assert not target.exists()
 save(PROJECT/'compiler_adoption.json',record);save(target,record)
 print('ADOPTED compiler profile',record['profile'],record['diagnostic_100'],flush=True)
if __name__=='__main__':main()
