"""Freeze joint pairing trials with functional/timing exclusions and preserved baselines."""
from pathlib import Path
import hashlib,json,shutil,zipfile
from archive_dual_types import ram_counts
from parse_dual_joint_timing import paths
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'docs/dual_joint'
GOOD=('ready','wait','fix','reg');ALL=GOOD+('branch',)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def verify(x):
 for k in ('input_sha256','actual_compile_sha256','ip_sha256'):
  for n,h in x.get(k,{}).items():
   p=ROOT/n;assert sha(p)==h,(k,n)
   if p.suffix!='.adf' and not n.replace('\\','/').startswith('simulation/results/load_bp_dual_joint'):copy(p,DEST/'inputs'/n)
def preserve(src,dest):
 for p in src.rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(src)
  if 'obj' in rel.parts or p.suffix in ('.vvp','.elf','.bin','.o','.exe','.pyc'):continue
  if rel.parts[0]=='pds' and rel.as_posix() not in ('pds/result.json','pds/run.tcl','pds/build.log','pds/report_timing/top.rtr','pds/device_map/top.dmr','pds/place_route/top.prr','pds/synthesize/apm_drm_lutram_utilization.log'):continue
  copy(p,dest/rel)

def main():
 DEST.mkdir(exist_ok=True);accepted=read(ROOT/'docs/accepted_dual_baseline.json');assert accepted['variant']=='dual_fwd_share'
 for key in ('source_sha256','evidence_sha256','ip_sha256'):
  for n,h in accepted[key].items():assert sha(ROOT/n)==h,(key,n)
 assert sha(ROOT/'docs/accepted_baseline.json')==accepted['single_issue_reference_sha256']
 assert sha(ROOT/'hardware/pds/report_timing/top.rtr')==accepted['single_issue_sta_sha256']
 for n,h in read(ROOT/'docs/accepted_baseline.json')['source_sha256'].items():assert sha(ROOT/n)==h,n
 prior={}
 for name in ('dual_fwd','dual_fan','dual_admit','dual_native','dual_types'):
  m=read(ROOT/'docs'/name/'manifest.json')
  for n,h in m.items():assert sha(ROOT/'docs'/name/n)==h,(name,n)
  prior[name]=len(m)
 for name in ('dual_native_decision.json','dual_types_decision.json','accepted_dual_baseline.json'):copy(ROOT/'docs'/name,DEST/name)
 parent=ROOT/'simulation/results/load_bp_dual_fwd_share';base=read(parent/'performance/result.json');bpds=read(parent/'pds/result.json');results={}
 generators={'ready':'generate_dual_joint.py','wait':'generate_dual_joint.py','branch':'generate_dual_joint.py','fix':'generate_dual_joint_fix.py','reg':'generate_dual_joint_reg.py'}
 for suffix in ALL:
  name='dual_joint_'+suffix;src=ROOT/('simulation/results/load_bp_'+name);g=read(src/'generation.json');verify(g)
  assert sha(ROOT/'tools'/generators[suffix])==g['generator_sha256']
  for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
  for p in (src/'ipcore').rglob('*'):
   if p.is_file() and p.suffix in ('.v','.idf'):assert sha(p)==sha(parent/'ipcore'/p.relative_to(src/'ipcore')),p
  for phase in ('performance','validation'):
   q=read(src/phase/'result.json');verify(q);assert q['status']=='PASS';assert q['override_sha256']==g['override_sha256'];ref=read(parent/phase/'result.json')
   for k in ('Retired instructions','Retired loads','Retired stores','BJP instructions','seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal'):assert q['metrics'][k]==ref['metrics'][k],(name,k)
   assert q['predictor']['resolved']==ref['predictor']['resolved']
  if suffix in GOOD:
   for sub,count in [('checks',63),('dual_checks',7),('pair_checks',6)]:
    q=read(src/sub/'result.json');verify(q);assert q['status']=='PASS' and len(q['tests'])==count,(name,sub)
   q=read(src/'audit/result.json');verify(q);assert q['status']=='PASS' and len(q['tests'])==10
   operands=src if suffix=='reg' else ROOT/'simulation/results/load_bp_dual_joint_wait'
   assert sha(src/'nc_operands.v')==sha(operands/'nc_operands.v')
   q=read(operands/'operand_checks/result.json');verify(q);assert q['status']=='PASS' and q['cycles']==300000
   if suffix in ('fix','reg'):
    q=read(src/'cancel_checks/result.json');verify(q);assert q['status']=='PASS' and len(q['tests'])==4
   if suffix=='reg':
    q=read(src/'protocol/result.json');verify(q);assert q['status']=='PASS' and len(q['tests'])==8
    q=read(src/'mul_protocol/result.json');verify(q);assert q['status']=='PASS' and len(q['tests'])==4
   target=ROOT/'simulation/results/dual_joint_paths'/name;q=read(target/'result.json');verify(q);assert q['status']=='PASS'
   for n,h in q['report_sha256'].items():assert sha(target/n)==h,n
   preserve(target,DEST/'targeted_paths'/name);target_paths=q['paths'];functional='PASS'
  else:
   q=read(src/'research_status.json');assert q['status']=='FUNCTIONAL_FAILED_NOT_ELIGIBLE';assert q['rtl_sha256']==g['override_sha256'];target_paths={};functional=q['status']
  q=read(src/'result.json');verify(q);pds=read(src/'pds/result.json');verify(pds);assert pds['pds_exit_code']==0;assert sha(src/'pds/run.tcl')==pds['tcl_sha256']
  cycles=int(q['metrics']['Stats window cycles']);retired=int(q['metrics']['Retired instructions']);d=q['dual'];gain=int(base['metrics']['Stats window cycles'])/cycles;ram=ram_counts(src/'pds/place_route/top_pnr.netlist');assert sum(ram.values())==pds['resources']['Distributed RAM']
  results[name]=dict(functional_status=functional,timing_status=pds['status'],cycles=cycles,ipc=retired/cycles,same_clock_gain_percent=(gain-1)*100,estimated_fmax_mhz=pds['estimated_fmax_mhz'],estimated_peak_gain_percent=(gain*pds['estimated_fmax_mhz']/bpds['estimated_fmax_mhz']-1)*100,break_even_fmax_mhz=bpds['estimated_fmax_mhz']/gain,resources=pds['resources'],ram_breakdown=ram,corners=pds['corners'],dual=d,joint=q['joint'],multiply=q['multiply'],predictor=q['predictor'],occupancy=dict(primary_issue_percent=d['groups_issued']/cycles*100,secondary_issue_percent=d['pairs_issued']/cycles*100,pair_given_primary_issue_percent=d['pairs_issued']/d['groups_issued']*100,primary_retire_percent=(retired-d['secondary_retired'])/cycles*100,secondary_retire_percent=d['secondary_retired']/cycles*100,secondary_instruction_share_percent=d['secondary_retired']/retired*100),slow_setup_paths=paths(src/'pds/report_timing/top.rtr'),targeted_paths=target_paths)
  preserve(src,DEST/name)
 for phase in ('performance','validation'):
  x=read(ROOT/f'simulation/results/load_bp_dual_joint_fix/{phase}/result.json');y=read(ROOT/f'simulation/results/load_bp_dual_joint_reg/{phase}/result.json')
  for k in ('metrics','dual','predictor','multiply','joint'):assert x[k]==y[k],(phase,k)
 snapshots={}
 with zipfile.ZipFile(DEST/'routed_snapshots.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
  for suffix in ALL:
   name='dual_joint_'+suffix
   for file in ('top_pnr.adf','top_pnr.netlist'):
    p=ROOT/f'simulation/results/load_bp_{name}/pds/place_route/{file}';n=name+'/'+file;z.write(p,n);snapshots[n]=sha(p)
 with zipfile.ZipFile(DEST/'routed_snapshots.zip') as z:
  for n,h in snapshots.items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 save(DEST/'routed_content_sha256.json',snapshots)
 for p in (ROOT/'tools').glob('*dual_joint*.py'):copy(p,DEST/'tools'/p.name)
 for name in ('archive_dual_types.py','archive_dual_issue.py','research_dual_issue.py','research_dual_ram_pds.py','check_dual_types_extra.py'):copy(ROOT/'tools'/name,DEST/'tools'/name)
 for p in (ROOT/'simulation/research/dual_joint').glob('*'):copy(p,DEST/'research'/p.name)
 eligible=[(x['estimated_peak_gain_percent'],n) for n,x in results.items() if x['functional_status']=='PASS' and x['timing_status']=='PASS' and x['estimated_peak_gain_percent']>0]
 save(DEST/'comparison.json',dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',accepted_dual_unchanged=True,preferred_research_candidate=max(eligible)[1] if eligible else 'dual_fwd_share',baseline_pds=bpds,prior_archives_verified=prior,candidates=results,limitations=[
 'One same-options physical run per immutable candidate; no seed sweep. Fmax estimated; actual PLL ~75MHz; no board/Flash/game validation; short CoreMark diagnostics.',
 'Rejected native/types rounds remain rejected. New combined designs reuse isolated, verified branch/MUL/window components under current authorization, not automatic adoption of old candidates.',
 'ready admits currently registered broadcasts only; wait/fix/reg may wait in existing two-entry queue for older ALU/load/MUL/DIV results, including lane1. No same-pair RAW/WAW allowed.',
 'Local SAT checks instruction/admission/decode identities; operand random tests compare against independent separate-value reference with direct current tags; not whole-core sequential formal equivalence.',
 'ready/wait/fix have byte-identical operand RTL, so one 3x100000-cycle operand test evidence is shared after exact hash check; reg has separate random tests and actual CPU future-tag protocol checks.',
 'branch prototype passed CoreMark but stalled fast-memory SoC random_17; excluded for functional failure despite its timing report. Registered redirect cancellation fixes annulled producer ledger in fix/reg; extra four-program cancellation/differential checks cover190 annulments.',
 'Dependency_split=0 means deferred waiting is admitted, not that programs have no dependencies. More paired instructions can increase operand/retirement waiting; issue and retired slot occupancy denominators differ.'
 ]))
 print(json.dumps({n:{k:x[k] for k in ('functional_status','timing_status','ipc','estimated_fmax_mhz','estimated_peak_gain_percent','resources')} for n,x in results.items()},indent=2))
def finish_manifest():
 copy(ROOT/'docs/dual_joint.md',DEST/'report.md');save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
if __name__=='__main__':main();finish_manifest()
