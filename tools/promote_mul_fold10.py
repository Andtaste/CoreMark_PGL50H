"""Independently rebuild and explicitly promote the measured successor baseline."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess
from verify_board_pnr import inspect
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'simulation/results/autonomous_20261022'
CANDIDATE=WORK/'mul_fold10';PROJECT=ROOT/'hardware/pds_optimized_mul_fold10_20261022'
ACTIVE=ROOT/'docs/active_optimization_baseline.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 global CANDIDATE,PROJECT
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','adopt']);p.add_argument('--name',choices=['mul_fold10','mul_early_products'],default='mul_fold10');a=p.parse_args()
 CANDIDATE=WORK/a.name;PROJECT=ROOT/f'hardware/pds_optimized_{a.name}_20261022'
 parent=json.loads((CANDIDATE/'parent_baseline.json').read_text());assert json.loads(ACTIVE.read_text())==parent,'Active baseline changed'
 for n,h in parent['input_sha256'].items():assert sha(ROOT/parent['project_directory']/n)==h,n
 if a.action=='build':
  assert not PROJECT.exists();PROJECT.mkdir()
  for folder in ('source','ipcore','constraints','memory'):shutil.copytree(CANDIDATE/folder,PROJECT/folder)
  s=(CANDIDATE/'new_core.pds').read_text();assert 'input_place_db_file' not in s
  (PROJECT/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',s))
  shutil.copyfile(CANDIDATE/'parent_baseline.json',PROJECT/'parent_baseline.json')
  with (PROJECT/'independent_build.log').open('wb') as f:subprocess.run(['E:/pango/PDS_2022.2-SP1-Lite/bin/pds_shell.exe','-project','new_core.pds','-run','report_timing'],cwd=PROJECT,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=3600)
  save(PROJECT/'verified_build.json',inspect(PROJECT));print('INDEPENDENT BUILD PASS');return
 assert 'Process "Report Timing" done.' in (PROJECT/'independent_build.log').read_text(errors='replace')
 for n,h in json.loads((WORK/'original_manifest.json').read_text()).items():assert sha(WORK/'original_board'/n)==h,n
 inputs={}
 for folder in ('source','ipcore','constraints','memory'):
  for f in (CANDIDATE/folder).rglob('*'):
   if f.is_file():
    n=str(f.relative_to(CANDIDATE));assert sha(f)==sha(PROJECT/n),n;inputs[n]=sha(f)
 sim=ROOT/f'simulation/results/load_bp_dual_boundary_auto_{a.name}';evidence={}
 generation=json.loads((sim/'generation.json').read_text())
 for n,h in generation['override_sha256'].items():
  rel=Path(n).relative_to(Path('hardware/pds'))
  assert sha(CANDIDATE/rel)==h and sha(sim/Path(n).name)==h,n
 evidence[str((sim/'generation.json').relative_to(ROOT))]=sha(sim/'generation.json')
 phases=['checks','performance','validation','pair_checks','mul_protocol','posted_soc_final','cancel_checks']
 if a.name=='mul_early_products':phases.append('mul_unit')
 for phase in phases:
  f=sim/phase/'result.json';x=json.loads(f.read_text());assert x['status']=='PASS',phase;evidence[str(f.relative_to(ROOT))]=sha(f)
  for n,h in x.get('input_sha256',{}).items():assert sha(ROOT/n)==h,(phase,n)
 first=inspect(CANDIDATE);second=inspect(PROJECT)
 for key in ('estimated_fmax_mhz','corners','routed_resources'):assert first[key]==second[key],key
 perf=json.loads((sim/'performance/result.json').read_text());m=perf['metrics'];cycles=int(m['Benchmark cycles64']);assert cycles<parent['benchmark_cycles']
 original=json.loads((ROOT/'simulation/results/load_bp_dual_boundary_auto_control/performance/result.json').read_text())
 assert perf['image_sha256']==original['image_sha256']
 variant='dual_boundary_mul_split_btb_fold10_clock82' if a.name=='mul_fold10' else 'dual_boundary_mul_early_products_btb_fold10_clock82'
 record=dict(status='ACCEPTED_OPTIMIZATION_BASELINE',variant=variant,source_trial=a.name,project_directory=str(PROJECT.relative_to(ROOT)),configured_cpu_hz=82000000,place_seed=3,route_seed=1,
  priority=parent['priority'],parent=parent['project_directory'],parent_backup=parent['parent_backup'],input_sha256=inputs,benchmark_cycles=cycles,stats_cycles=int(m['Stats window cycles']),retired=int(m['Retired instructions']),ipc=int(m['Retired instructions'])/int(m['Stats window cycles']),cm_per_mhz=10e6/cycles,
  same_clock_throughput_gain_pct=100*(parent['benchmark_cycles']/cycles-1),gain_vs_original_board_pct=100*(int(original['metrics']['Benchmark cycles64'])/cycles-1),estimated_fmax_mhz=second['estimated_fmax_mhz'],resources=second['routed_resources'],corners=second['corners'],physical_verification=second,independent_native_runs=2,test_evidence=evidence,
  scope='Fixed10/fixed1 diagnostic simulations; unchanged binaries and compiler flags; actual82MHz PLL, board pins and two independent native builds. No board programming or official long-run CoreMark score.',build_command='tools/run.ps1 -Task pds')
 save(PROJECT/'parent_baseline.json',parent);save(CANDIDATE/'adoption.json',record);save(PROJECT/'verified_build.json',second);save(ACTIVE,record)
 print('ADOPTED',record['variant'],record['same_clock_throughput_gain_pct'])
if __name__=='__main__':main()
