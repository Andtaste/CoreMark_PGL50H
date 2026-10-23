"""Adopt only after independent native rebuild and all recorded checks pass."""
from pathlib import Path
import hashlib,json,shutil
from verify_board_pnr import inspect
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'simulation/results/autonomous_20261022'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 candidate=WORK/'btb_fold';project=ROOT/'hardware/pds_optimized_20261022';sim=ROOT/'simulation/results/load_bp_dual_boundary_auto_btb_fold'
 assert 'Process "Report Timing" done.' in (project/'independent_build.log').read_text(errors='replace')
 original_manifest=json.loads((WORK/'original_manifest.json').read_text())
 for n,h in original_manifest.items():assert sha(WORK/'original_board'/n)==h,n
 inputs={}
 for folder in ('source','ipcore','constraints','memory'):
  for p in (candidate/folder).rglob('*'):
   if p.is_file():
    n=p.relative_to(candidate);assert sha(p)==sha(project/n),n;inputs[str(n)]=sha(p)
  for p in (WORK/'original_board'/folder).rglob('*'):
   if p.is_file():assert sha(p)==sha(ROOT/'hardware/pds_board5000'/p.relative_to(WORK/'original_board')),p
 evidence={}
 for sub in ('checks','performance','validation','posted_soc_final','pair_checks','cancel_checks'):
  p=sim/sub/'result.json';x=json.loads(p.read_text());assert x['status']=='PASS',(sub,x)
  evidence[str(p.relative_to(ROOT))]=sha(p)
 first=inspect(candidate);second=inspect(project)
 for k in ('estimated_fmax_mhz','corners','routed_resources'):assert first[k]==second[k],k
 perf=json.loads((sim/'performance/result.json').read_text())
 baseline=json.loads((ROOT/'simulation/results/load_bp_dual_boundary_auto_control/performance/result.json').read_text())
 cycles=int(perf['metrics']['Benchmark cycles64']);old=int(baseline['metrics']['Benchmark cycles64']);assert cycles<old
 record=dict(status='ACCEPTED_OPTIMIZATION_BASELINE',variant='dual_boundary_pairbranch_btb_fold_clock82',project_directory=str(project.relative_to(ROOT)),configured_cpu_hz=82000000,place_seed=3,route_seed=1,
  priority=['total_throughput','clock_mhz','cm_per_mhz','resources'],parent='hardware/pds_board5000',parent_backup=str((WORK/'original_board').relative_to(ROOT)),input_sha256=inputs,
  benchmark_cycles=cycles,stats_cycles=int(perf['metrics']['Stats window cycles']),retired=int(perf['metrics']['Retired instructions']),ipc=int(perf['metrics']['Retired instructions'])/int(perf['metrics']['Stats window cycles']),cm_per_mhz=10e6/cycles,same_clock_throughput_gain_pct=100*(old/cycles-1),
  estimated_fmax_mhz=second['estimated_fmax_mhz'],resources=second['routed_resources'],corners=second['corners'],physical_verification=second,independent_native_runs=2,test_evidence=evidence,
  scope='Fixed10 and fixed1 diagnostic simulation, actual82MHz PLL, actual board pins, two native source-to-route runs. No board programming or long-run CoreMark claim.',build_command='tools/run.ps1 -Task pds')
 previous=ROOT/'docs/active_optimization_baseline.json'
 assert not previous.exists(),'An active optimization baseline already exists; do not overwrite blindly'
 save(previous,record);save(project/'verified_build.json',second);save(WORK/'adoption.json',record)
 comparison=json.loads((WORK/'comparison.json').read_text())
 for row in comparison['candidates']:
  if row['name']=='btb_fold':row['decision']='ADOPTED'
  if row['name']=='control':row['decision']='PRESERVED_PARENT'
 save(WORK/'comparison.json',comparison)
 print('ADOPTED',record['variant'],record['same_clock_throughput_gain_pct'])
if __name__=='__main__':main()
