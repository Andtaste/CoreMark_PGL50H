"""Verify, compare and compactly archive secondary LSU trials without adoption."""
from pathlib import Path
import hashlib,json,shutil,zipfile,re
from parse_dual_joint_timing import paths
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'docs/dual_lsu'
NAMES=['dual_lsu_'+n for n in ('shared','ports','forward','pair')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def main():
 assert not (DEST/'manifest.json').exists(),'Archive already frozen';DEST.mkdir(exist_ok=True)
 resolutions=[]
 def verify(x,origin):
  for key in ('input_sha256','actual_compile_sha256','ip_sha256','canonical_sha256'):
   for n,h in x.get(key,{}).items():
    p=ROOT/n;assert p.is_file(),(origin,n)
    if sha(p)!=h:
     # The ports preflight used a mixed wire declaration rejected by Icarus.
     # Both spelling variants of the path survived in canonical metadata.
     assert key=='canonical_sha256' and n.replace('\\','/')=='simulation/research/dual_lsu/nc_local_bus.v' and h=='a3b99413cb2f2ca1715097e7e2059f992b24fac8686462e3934ac7ed4c6d01bb',(origin,n,h,sha(p))
     old=p.read_bytes().replace(b'wire uart_ready;wire uart_addr=',b'wire uart_ready,uart_addr=');assert hashlib.sha256(old).hexdigest()==h
     q=DEST/'source_versions'/h/p.name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(old)
     resolutions.append(dict(evidence=origin,input=n,sha256=h,archived_source=str(q.relative_to(DEST)),reason='Rejected preflight declaration; actual compiled override and current canonical hash are separately verified.'));continue
    if not n.replace('\\','/').startswith('simulation/results/load_bp_dual_lsu_') and p.suffix!='.adf':copy(p,DEST/'inputs'/n)
 accepted=read(ROOT/'docs/accepted_dual_baseline.json');assert accepted['variant']=='dual_fwd_share'
 for key in ('source_sha256','evidence_sha256','ip_sha256'):
  for n,h in accepted[key].items():assert sha(ROOT/n)==h,(key,n)
 assert sha(ROOT/'docs/accepted_baseline.json')==accepted['single_issue_reference_sha256']
 assert sha(ROOT/'hardware/pds/report_timing/top.rtr')==accepted['single_issue_sta_sha256']
 for n,h in read(ROOT/'docs/accepted_baseline.json')['source_sha256'].items():assert sha(ROOT/n)==h,n
 prior={}
 for name in ('dual_fwd','dual_fan','dual_admit','dual_native','dual_types','dual_joint','dual_split','dual_legacy'):
  m=read(ROOT/'docs'/name/'manifest.json')
  for n,h in m.items():assert sha(ROOT/'docs'/name/n)==h,(name,n)
  prior[name]=len(m)
 rows={};basecycles=accepted['coremark_stats_cycles'];control=read(ROOT/'docs/dual_legacy/comparison.json')['candidates']['dual_legacy_fifo']
 for name in NAMES:
  src=ROOT/('simulation/results/load_bp_'+name);g=read(src/'generation.json');verify(g,name+'/generation')
  assert sha(ROOT/'docs/accepted_dual_baseline.json')==g['accepted_dual_sha256']
  for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
  gen='generate_dual_lsu'+('_forward' if name.endswith('_forward') else '_pair' if name.endswith('_pair') else '')+'.py';assert sha(ROOT/'tools'/gen)==g['generator_sha256']
  counts={}
  for sub,num in [('checks',63),('dual_checks',7),('pair_checks',6),('cancel_checks',4),('bus_checks',3),('directed_checks',3),('stats_checks',1),('audit_checks',4),('operands_checks',1 if name in NAMES[:2] else 3),('contract_checks',3 if name in NAMES[:2] else 6 if name.endswith('_forward') else 7)]:
   x=read(src/sub/'result.json');verify(x,name+'/'+sub);assert x['status']=='PASS' and len(x['tests'])==num,(name,sub);counts[sub]=num
  for phase in ('performance','validation'):
   x=read(src/phase/'result.json');verify(x,name+'/'+phase);assert x['status']=='PASS' and x['override_sha256']==g['override_sha256'];ref=read(ROOT/f'simulation/results/load_bp_dual_fwd_share/{phase}/result.json')
   for k in ('Retired instructions','Retired loads','Retired stores','BJP instructions','seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal'):assert x['metrics'][k]==ref['metrics'][k],(name,phase,k)
  if name in NAMES[2:]:
   x=read(src/'redundancy_checks/result.json');verify(x,name+'/redundancy');assert x['status']=='PASS';counts['redundancy_checks']=len(x['tests'])
  sim=read(src/'performance/result.json');pd=read(src/'pds/result.json');verify(pd,name+'/pds');assert pd['pds_exit_code']==0 and sha(src/'pds/run.tcl')==pd['tcl_sha256']
  queries={}
  for sub in ('targeted_paths','lsu_paths'):
   q=read(src/sub/'result.json');verify(q,name+'/'+sub);assert q['status']=='PASS'
   for n,h in q['report_sha256'].items():assert sha(src/sub/n)==h
   queries[sub]=q['paths']
  ram={}
  for inst,kind in re.findall(r'^([^;\r\n]+);(gopRAM\w+)',(src/'pds/place_route/top_pnr.netlist').read_text(errors='replace'),re.M):
   cat='instruction_fifo' if '/fetch/even_inst' in inst or '/fetch/odd_inst' in inst else 'btb' if '/predictor.' in inst else 'regfile' if '/rf/' in inst else 'exmem_fifo' if '/memory_queue/' in inst else inst
   ram[cat]=ram.get(cat,0)+1
  assert sum(ram.values())==pd['resources']['Distributed RAM']
  cycles=int(sim['metrics']['Stats window cycles']);retired=int(sim['metrics']['Retired instructions']);side=sim['dual']['secondary_retired'];fmax=pd['estimated_fmax_mhz']
  rows[name]=dict(functional_status='PASS',timing_status=pd['status'],cycles=cycles,ipc=retired/cycles,retired=retired,secondary_retired=side,same_clock_gain_percent=(basecycles/cycles-1)*100,vs_fifo_same_clock_percent=(control['cycles']/cycles-1)*100,estimated_fmax_mhz=fmax,estimated_peak_gain_percent=(basecycles/cycles*fmax/accepted['estimated_fmax_mhz']-1)*100,resources=pd['resources'],corners=pd['corners'],ram_breakdown=ram,occupancy=dict(primary_retire_percent=(retired-side)/cycles*100,secondary_retire_percent=side/cycles*100,pair_given_primary_issue_percent=sim['dual']['pairs_issued']/sim['dual']['groups_issued']*100,secondary_share_of_retired_percent=side/retired*100),dual=sim['dual'],lsu=sim['lsu'],multiply=sim['multiply'],predictor=sim['predictor'],wait_metrics={k:sim['metrics'][k] for k in ('EX operand wait','ID blocked cycles','MEM occupied cycles','IF queue empty')},checks=counts,slow_setup_paths=paths(src/'pds/report_timing/top.rtr'),targeted_paths=queries['targeted_paths'],lsu_paths=queries['lsu_paths'],directed_coverage=read(src/'directed_checks/result.json')['coverage'])
  for p in src.rglob('*'):
   if not p.is_file():continue
   rel=p.relative_to(src)
   if 'obj' in rel.parts or p.suffix in ('.vvp','.elf','.bin','.o','.exe','.pyc'):continue
   if rel.parts[0]=='pds' and rel.as_posix() not in ('pds/result.json','pds/run.tcl','pds/build.log','pds/report_timing/top.rtr','pds/device_map/top.dmr','pds/place_route/top.prr','pds/synthesize/apm_drm_lutram_utilization.log'):continue
   copy(p,DEST/name/rel)
 snapshots={}
 with zipfile.ZipFile(DEST/'routed_snapshots.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
  for name in NAMES:
   for file in ('top_pnr.adf','top_pnr.netlist'):
    p=ROOT/f'simulation/results/load_bp_{name}/pds/place_route/{file}';n=name+'/'+file;z.write(p,n);snapshots[n]=sha(p)
 with zipfile.ZipFile(DEST/'routed_snapshots.zip') as z:
  for n,h in snapshots.items():assert hashlib.sha256(z.read(n)).hexdigest()==h
 save(DEST/'routed_content_sha256.json',snapshots)
 for p in (ROOT/'tools').glob('*dual_lsu*.py'):copy(p,DEST/'tools'/p.name)
 for n in ('research_dual_issue.py','research_dual_ram_pds.py','report_dual_legacy_paths.py','check_dual_joint_cancel.py','check_dual_joint_pairs.py','check_dual_native_extra.py','parse_dual_joint_timing.py'):copy(ROOT/'tools'/n,DEST/'tools'/n)
 for n in ('accepted_dual_baseline.json','accepted_baseline.json'):copy(ROOT/'docs'/n,DEST/n)
 suite=ROOT/'simulation/results/dual_lsu_suite'
 final=read(suite/'final_result.json');assert final['status']=='PASS'
 for p in suite.iterdir():
  if p.is_file():copy(p,DEST/'suite'/p.name)
 cleanup=[read(ROOT/'simulation'/n) for n in ('cleanup_result.json','cleanup_completed_lsu_result.json')]
 save(DEST/'cleanup.json',dict(removed_directories=sum(x['removed_directories'] for x in cleanup),reclaimed_bytes=sum(x['reclaimed_bytes'] for x in cleanup),operations=cleanup))
 save(DEST/'comparison.json',dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',accepted_variant_unchanged='dual_fwd_share',accepted_descriptor_sha256=sha(ROOT/'docs/accepted_dual_baseline.json'),prior_archives_verified=prior,source_version_resolutions=resolutions,candidates=rows,window_control=control,limits=[
 'Fixed 1- and 10-iteration diagnostic images, same hash as accepted new core; short runs are not official CoreMark scores. No board/game/Flash execution verified.',
 'One PDS implementation per candidate with unchanged PLL 75MHz and constraints; no seed sweep. Timing-failed estimates are hypothetical throughput figures, not validated operating points.',
 'Secondary LSU is fault-free local BRAM only; MMIO, range and alignment split/replay to primary. Pair candidate additionally requires an explicit accepted primary nofault guarantee before speculative younger stores.',
 'No EX early request or combinational RAM-return-to-EX bypass. Registered load completion forwards on the following cycle; primary and side architectural retirement remain grouped.',
 'Redundancy audit found L1 registered completion never earlier than existing W1 in this grouped-retirement design. An 8-cycle arbitrary-input bounded proof checks same-cycle clean W1 tag/data equivalence, and directed runs observe zero early L1. L0 does provide earlier completion while waiting on a side store. No performance claim is made for removing L1 without a separate implementation run.',
 'Memory ready no longer requires valid in forward/pair. Thus MEM occupied counters include an empty-FIFO artifact in shared/ports; their large absolute change must not be interpreted as a physical stall reduction.',
 'Original extra test monitored side valid at fault WB. New memory suppresses side before WB, so observer was adapted to primary-error completion with held-side valid; assembly still independently checks causes, EPC and unchanged younger destination.',
 'Initial targeted lsu_request used unmatched ADDRA/ADDRB endpoint patterns and PDS returned unrestricted paths. Do not interpret that field as LSU timing. lsu_paths uses verified ADA/ADB primitive names and asserts every returned endpoint/source matches.',
 'Initial targeted lsu_feedback includes bus interrupt/timer sources; use lsu_paths/memory_to_core for memory register sources. Other targeted paths are intentionally broad selection reports.',
 'Historical and completed-trial Verilator obj caches removed only after fixed-image tests completed; all hashes, logs, traces and compact routed snapshots preserved.'
 ]))
 print(json.dumps({n:{k:x[k] for k in ('ipc','estimated_fmax_mhz','timing_status','resources')} for n,x in rows.items()},indent=2))
def finish():
 copy(ROOT/'docs/dual_lsu.md',DEST/'report.md');save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
if __name__=='__main__':main()
