"""Freeze source-wait profiling and ID-split trials without adopting a candidate."""
from pathlib import Path
import json,hashlib,zipfile
import archive_dual_joint as archive
from archive_dual_types import ram_counts
from parse_dual_joint_timing import paths
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'docs/dual_split';archive.DEST=DEST
sha,read,save,copy,verify,preserve=archive.sha,archive.read,archive.save,archive.copy,archive.verify,archive.preserve

def main():
 DEST.mkdir(exist_ok=True);a=read(ROOT/'docs/accepted_dual_baseline.json');assert a['variant']=='dual_fwd_share'
 for k in ['source_sha256','evidence_sha256','ip_sha256']:
  for n,h in a[k].items():assert sha(ROOT/n)==h,(k,n)
 assert sha(ROOT/'docs/accepted_baseline.json')==a['single_issue_reference_sha256']
 assert sha(ROOT/'hardware/pds/report_timing/top.rtr')==a['single_issue_sta_sha256']
 for n,h in read(ROOT/'docs/accepted_baseline.json')['source_sha256'].items():assert sha(ROOT/n)==h,n
 prior={}
 for name in ['dual_fwd','dual_fan','dual_admit','dual_native','dual_types','dual_joint']:
  m=read(ROOT/'docs'/name/'manifest.json')
  for n,h in m.items():assert sha(ROOT/'docs'/name/n)==h,(name,n)
  prior[name]=len(m)
 parent=ROOT/'simulation/results/load_bp_dual_joint_fix';pbase=read(parent/'performance/result.json');ppds=read(parent/'pds/result.json');base=read(ROOT/'simulation/results/load_bp_dual_fwd_share/performance/result.json');bpds=read(ROOT/'simulation/results/load_bp_dual_fwd_share/pds/result.json')
 cycle_src=ROOT/'simulation/results/dual_split_load_cycles';cycle=read(cycle_src/'result.json');verify(cycle);assert cycle['status']=='PASS';preserve(cycle_src,DEST/'load_cycles')
 probes={}
 for suffix in ['probe','full']:
  src=ROOT/('simulation/results/load_bp_dual_wait_'+suffix);q=read(src/'performance/result.json');verify(q)
  assert q['parent_profile_identical'] and q['status']=='PASS'
  for k in ['metrics','dual','multiply','predictor']:assert q[k]==pbase[k]
  assert q['override_sha256']==pbase['override_sha256'];assert q['wait_kinds']['all']==813816
  preserve(src,DEST/('wait_'+suffix));probes[suffix]=q['wait_kinds']
 for k,v in probes['probe'].items():assert probes['full'][k]==v,k
 results={};snapshots={}
 for suffix in ['ready','slow']:
  name='dual_split_'+suffix;src=ROOT/('simulation/results/load_bp_'+name);g=read(src/'generation.json');verify(g)
  assert sha(ROOT/'tools/generate_dual_split.py')==g['generator_sha256']
  for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
  assert sha(src/'nc_operands.v')==sha(parent/'nc_operands.v')
  evidence=read(parent.parent/'load_bp_dual_joint_wait/operand_checks/result.json');verify(evidence);assert evidence['status']=='PASS' and evidence['cycles']==300000
  assert sha(parent.parent/'load_bp_dual_joint_wait/nc_operands.v')==sha(src/'nc_operands.v')
  for sub,n in [('checks',63),('dual_checks',7),('pair_checks',6),('policy_checks',4),('cancel_checks',4)]:
   q=read(src/sub/'result.json');verify(q);assert q['status']=='PASS' and len(q['tests'])==n,(name,sub)
  q=read(src/'audit/result.json');verify(q);assert q['status']=='PASS' and len(q['tests'])==10
  for phase in ['performance','validation']:
   q=read(src/phase/'result.json');verify(q);assert q['status']=='PASS';assert q['override_sha256']==g['override_sha256'];ref=read(parent/phase/'result.json')
   for k in ['Retired instructions','Retired loads','Retired stores','BJP instructions','seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal']:assert q['metrics'][k]==ref['metrics'][k],(name,k)
  pds=read(src/'pds/result.json');verify(pds);assert pds['pds_exit_code']==0;assert sha(src/'pds/run.tcl')==pds['tcl_sha256']
  target=ROOT/'simulation/results/dual_split_paths'/name;t=read(target/'result.json');verify(t);assert t['status']=='PASS'
  for n,h in t['report_sha256'].items():assert sha(target/n)==h,n
  preserve(target,DEST/'targeted_paths'/name)
  sim=read(src/'performance/result.json');cycles=int(sim['metrics']['Stats window cycles']);retired=int(sim['metrics']['Retired instructions']);d=sim['dual'];ram=ram_counts(src/'pds/place_route/top_pnr.netlist');assert sum(ram.values())==pds['resources']['Distributed RAM']
  gain=int(base['metrics']['Stats window cycles'])/cycles;pgain=int(pbase['metrics']['Stats window cycles'])/cycles
  results[name]=dict(cycles=cycles,ipc=retired/cycles,same_clock_vs_accepted_percent=(gain-1)*100,same_clock_vs_joint_percent=(pgain-1)*100,estimated_fmax_mhz=pds['estimated_fmax_mhz'],timing_status=pds['status'],estimated_peak_vs_accepted_percent=(gain*pds['estimated_fmax_mhz']/bpds['estimated_fmax_mhz']-1)*100,estimated_peak_vs_joint_percent=(pgain*pds['estimated_fmax_mhz']/ppds['estimated_fmax_mhz']-1)*100,resources=pds['resources'],corners=pds['corners'],ram_breakdown=ram,dual=d,joint=sim['joint'],multiply=sim['multiply'],predictor=sim['predictor'],wait_metrics={k:sim['metrics'][k] for k in ['EX operand wait','ID blocked cycles','MEM occupied cycles']},occupancy=dict(primary_retire_percent=(retired-d['secondary_retired'])/cycles*100,secondary_retire_percent=d['secondary_retired']/cycles*100,pair_given_primary_percent=d['pairs_issued']/d['groups_issued']*100),slow_setup_paths=paths(src/'pds/report_timing/top.rtr'),targeted_paths=t['paths'])
  preserve(src,DEST/name)
 with zipfile.ZipFile(DEST/'routed_snapshots.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
  for name in results:
   for file in ['top_pnr.adf','top_pnr.netlist']:
    p=ROOT/f'simulation/results/load_bp_{name}/pds/place_route/{file}';n=name+'/'+file;z.write(p,n);snapshots[n]=sha(p)
 with zipfile.ZipFile(DEST/'routed_snapshots.zip') as z:
  for n,h in snapshots.items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 save(DEST/'routed_content_sha256.json',snapshots)
 for glob in ['*dual_split*.py','*dual_wait*.py']:
  for p in (ROOT/'tools').glob(glob):copy(p,DEST/'tools'/p.name)
 for name in ['archive_dual_joint.py','archive_dual_types.py','archive_dual_issue.py','parse_dual_joint_timing.py','check_dual_joint_cancel.py','profile_dual_joint.py','check_dual_types_extra.py','research_dual_issue.py','research_dual_ram_pds.py']:copy(ROOT/'tools'/name,DEST/'tools'/name)
 copy(ROOT/'docs/accepted_dual_baseline.json',DEST/'accepted_dual_baseline.json')
 save(DEST/'comparison.json',dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',accepted_variant_unchanged='dual_fwd_share',parent_joint_variant='dual_joint_fix',parent_joint_cycles=3094782,parent_joint_fmax_mhz=79.942,accepted_cycles=3458702,accepted_fmax_mhz=87.789,prior_archives_verified=prior,wait_kinds=probes['full'],load_cycle_measurements=cycle['directed'],candidates=results,limits=[
 'ID splits before allocating a retirement group. The younger word remains at sliding IF head; main still waits for its own operands. No post-ID partial execution, re-tagging, or independent retirement was added.',
 'ready admits dependent side sources only when a currently registered F/F1/M/W/W1 broadcast matches; slow rejects any selected live load/MUL/DIV producer even if its result may already be available. slow still allows older ordinary-ALU waits; not a universal side-ready policy.',
 'All four-source operand RTL identical to prior passing joint version; one exact-hash shared 300000-cycle random queue test evidence is referenced. Policy-specific assertions and capture-after-push checks are new.',
 'Probe RTL and images are byte-identical to joint fix; metrics/dual/multiply/predictor match exactly. Categories may overlap, and response-now counter counts operands, not unique cycles or loads. Waiting exposure is not an estimate of saved cycles.',
 'Initial monitor using dynamic hierarchical unpacked-array indexing triggered Verilator internal fault. Replaced bench reads by static-index alternatives; retained diagnostic; no RTL changed.',
 'No early RAM return or early LSU issue was implemented here. Prior early-start trial remains rejected; no reuse as adopted code. RTL/PLL/images/vendor IP/physical RAM/DSP counts unchanged except isolated admission changes.',
 'One PDS run per immutable candidate, same options/constraints, no seed sweep. Frequency estimated; short CoreMark diagnostic, no board/game/Flash validation.'
 ]))
 print(json.dumps(results,indent=2)[:4500])
def finish_manifest():
 copy(ROOT/'docs/dual_split.md',DEST/'report.md');save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
if __name__=='__main__':main();finish_manifest()
