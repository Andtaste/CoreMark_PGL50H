"""Verify and freeze integrated word-FIFO/forwarding trials without adoption."""
from pathlib import Path
import hashlib,json,shutil,zipfile,re
from parse_dual_joint_timing import paths
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'docs/dual_legacy'
NAMES=['dual_legacy_'+n for n in ('fifo','return','split','word','select')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def main():
 assert not (DEST/'manifest.json').exists(),'Archive already frozen';DEST.mkdir(exist_ok=True)
 # Preserve the exact pre-SAT harness used by early runs, instead of editing
 # historical hashes or rerunning unchanged simulations for bookkeeping.
 checker=ROOT/'tools/check_dual_legacy.py';s=checker.read_text();start=s.index("  fun=fetch[fetch.index(' function[8:0] classify_parts'):");end=s.index("  if a.variant!='dual_legacy_fifo':",start)
 old=(s[:start]+s[end:]).encode();oldhash=hashlib.sha256(old).hexdigest();assert oldhash=='6dcef38ba96a5177d5c333c6d783f77efea57a0e20c9ba96f98595de98073666',oldhash
 version=DEST/'tool_versions'/oldhash/'check_dual_legacy.py';version.parent.mkdir(parents=True,exist_ok=True);version.write_bytes(old);resolutions=[]
 def verify(x,origin):
  for key in ('input_sha256','actual_compile_sha256','ip_sha256'):
   for n,h in x.get(key,{}).items():
    p=ROOT/n;assert p.is_file(),(origin,n)
    if sha(p)!=h:
     assert n.replace('\\','/')=='tools/check_dual_legacy.py' and h==oldhash,(origin,n,h,sha(p));resolutions.append(dict(evidence=origin,input=n,sha256=h,archived_source=str(version.relative_to(DEST))));continue
    if not n.replace('\\','/').startswith('simulation/results/load_bp_dual_legacy_') and p.suffix!='.adf':copy(p,DEST/'inputs'/n)
 accepted=read(ROOT/'docs/accepted_dual_baseline.json');assert accepted['variant']=='dual_fwd_share'
 for key in ('source_sha256','evidence_sha256','ip_sha256'):
  for n,h in accepted[key].items():assert sha(ROOT/n)==h,(key,n)
 assert sha(ROOT/'docs/accepted_baseline.json')==accepted['single_issue_reference_sha256'];assert sha(ROOT/'hardware/pds/report_timing/top.rtr')==accepted['single_issue_sta_sha256']
 for n,h in read(ROOT/'docs/accepted_baseline.json')['source_sha256'].items():assert sha(ROOT/n)==h,n
 prior={}
 for name in ('dual_fwd','dual_fan','dual_admit','dual_native','dual_types','dual_joint','dual_split'):
  m=read(ROOT/'docs'/name/'manifest.json')
  for n,h in m.items():assert sha(ROOT/'docs'/name/n)==h,(name,n)
  prior[name]=len(m)
 base=read(ROOT/'simulation/results/load_bp_dual_fwd_share/performance/result.json');bp=read(ROOT/'simulation/results/load_bp_dual_fwd_share/pds/result.json');joint=read(ROOT/'simulation/results/load_bp_dual_joint_fix/performance/result.json');rows={};snapshots={}
 for name in NAMES:
  src=ROOT/('simulation/results/load_bp_'+name);g=read(src/'generation.json');verify(g,name+'/generation')
  for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
  gen='generate_dual_legacy'+('_word' if name.endswith('_word') else '_select' if name.endswith('_select') else '')+'.py';assert sha(ROOT/'tools'/gen)==g['generator_sha256']
  counts={}
  for sub,expected in [('checks',63),('dual_checks',7),('pair_checks',6),('cancel_checks',4),('timeline_checks',4),('audit_checks',4 if name.endswith('_fifo') else 5)]:
   x=read(src/sub/'result.json');verify(x,name+'/'+sub);assert x['status']=='PASS' and len(x['tests'])==expected,(name,sub);counts[sub]=len(x['tests'])
  operand=ROOT/'simulation/results/load_bp_dual_legacy_return/operands_checks' if name.endswith('_word') else src/('operand_checks' if name.endswith('_fifo') else 'operands_checks')
  x=read(operand/'result.json');verify(x,name+'/operands');assert x['status']=='PASS' and len(x['tests'])==3
  op_name='dual_legacy_return' if name.endswith('_word') else name
  actual=Path(next(n for n in x['input_sha256'] if n.replace('\\','/').endswith('/load_bp_'+op_name+'/nc_operands.v')));assert sha(ROOT/actual)==sha(src/'nc_operands.v');counts['operand_random_cycles']=300000
  if name.endswith('_select'):
   x=read(src/'protocol_checks/result.json');verify(x,name+'/protocol');assert x['status']=='PASS' and len(x['tests'])==5;counts['protocol_checks']=5
  for phase in ('performance','validation'):
   x=read(src/phase/'result.json');verify(x,name+'/'+phase);assert x['status']=='PASS' and x['override_sha256']==g['override_sha256'];ref=read(ROOT/f'simulation/results/load_bp_dual_fwd_share/{phase}/result.json')
   for k in ('Retired instructions','Retired loads','Retired stores','BJP instructions','seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal'):assert x['metrics'][k]==ref['metrics'][k],(name,phase,k)
  sim=read(src/'performance/result.json');pd=read(src/'pds/result.json');verify(pd,name+'/pds');assert (pd['pds_exit_code']==0 or pd['status']=='PDS_TIMEOUT') and sha(src/'pds/run.tcl')==pd['tcl_sha256']
  q={'paths':{}};ram=None
  if pd['status']!='PDS_TIMEOUT':
   q=read(src/'targeted_paths/result.json');verify(q,name+'/targeted_paths')
   for n,h in q['report_sha256'].items():assert sha(src/'targeted_paths'/n)==h
   ram={}
   for inst,kind in re.findall(r'^([^;\r\n]+);(gopRAM\w+)',(src/'pds/place_route/top_pnr.netlist').read_text(errors='replace'),re.M):
    cat='instruction_fifo' if '/fetch/even_inst' in inst or '/fetch/odd_inst' in inst else 'btb' if '/predictor.' in inst else 'regfile' if '/rf/' in inst else 'exmem_fifo' if '/memory_queue/' in inst else 'slow_class' if '/slow_main' in inst or '/slow_side' in inst else inst
    ram[cat]=ram.get(cat,0)+1
   assert sum(ram.values())==pd['resources']['Distributed RAM'],name
  cycles=int(sim['metrics']['Stats window cycles']);retired=int(sim['metrics']['Retired instructions']);side=sim['dual']['secondary_retired'];gain=int(base['metrics']['Stats window cycles'])/cycles
  rows[name]=dict(functional_status='PASS',timing_status=pd['status'],cycles=cycles,ipc=retired/cycles,retired=retired,same_clock_gain_percent=(gain-1)*100,vs_joint_same_clock_percent=(int(joint['metrics']['Stats window cycles'])/cycles-1)*100,estimated_fmax_mhz=pd['estimated_fmax_mhz'],estimated_peak_gain_percent=(gain*pd['estimated_fmax_mhz']/bp['estimated_fmax_mhz']-1)*100 if pd['estimated_fmax_mhz'] else None,resources=pd['resources'],corners=pd['corners'],ram_breakdown=ram,occupancy=dict(primary_retire_percent=(retired-side)/cycles*100,secondary_retire_percent=side/cycles*100,pair_given_primary_issue_percent=sim['dual']['pairs_issued']/sim['dual']['groups_issued']*100),dual=sim['dual'],multiply=sim['multiply'],predictor=sim['predictor'],slot_mix=sim['joint'],wait_metrics={k:sim['metrics'][k] for k in ('EX operand wait','ID blocked cycles','MEM occupied cycles')},checks=counts,slow_setup_paths=paths(src/'pds/report_timing/top.rtr') if pd['status']!='PDS_TIMEOUT' else [],targeted_paths=q['paths'],timeline=read(src/'timeline_checks/result.json')['tests'])
  for p in src.rglob('*'):
   if not p.is_file():continue
   rel=p.relative_to(src)
   if 'obj' in rel.parts or p.suffix in ('.vvp','.elf','.bin','.o','.exe','.pyc'):continue
   if rel.parts[0]=='pds' and rel.as_posix() not in ('pds/result.json','pds/run.tcl','pds/build.log','pds/report_timing/top.rtr','pds/device_map/top.dmr','pds/place_route/top.prr','pds/synthesize/apm_drm_lutram_utilization.log'):continue
   copy(p,DEST/name/rel)
 for phase in ('performance','validation'):
  a=read(ROOT/f'simulation/results/load_bp_dual_legacy_word/{phase}/result.json');b=read(ROOT/f'simulation/results/load_bp_dual_legacy_select/{phase}/result.json')
  for k in ('metrics','dual','multiply','predictor','joint'):assert a[k]==b[k],(phase,k)
 with zipfile.ZipFile(DEST/'routed_snapshots.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
  for name in NAMES:
   if rows[name]['timing_status']=='PDS_TIMEOUT':continue
   for file in ('top_pnr.adf','top_pnr.netlist'):
    p=ROOT/f'simulation/results/load_bp_{name}/pds/place_route/{file}'
    if not p.exists():continue
    n=name+'/'+file;z.write(p,n);snapshots[n]=sha(p)
 with zipfile.ZipFile(DEST/'routed_snapshots.zip') as z:
  for n,h in snapshots.items():assert hashlib.sha256(z.read(n)).hexdigest()==h
 save(DEST/'routed_content_sha256.json',snapshots)
 for p in (ROOT/'tools').glob('*dual_legacy*.py'):copy(p,DEST/'tools'/p.name)
 for n in ('research_dual_issue.py','research_dual_ram_pds.py','profile_dual_joint.py','check_dual_joint_cancel.py','check_dual_joint_pairs.py','check_dual_joint_operands.py','check_dual_native_extra.py','parse_dual_joint_timing.py'):copy(ROOT/'tools'/n,DEST/'tools'/n)
 copy(ROOT/'docs/accepted_dual_baseline.json',DEST/'accepted_dual_baseline.json')
 save(DEST/'comparison.json',dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',accepted_variant_unchanged='dual_fwd_share',prior_archives_verified=prior,source_version_resolutions=resolutions,candidates=rows,limits=[
 'One fixed 1-iteration image and one fixed 10-iteration image, identical between candidates and accepted new core. Original old-core image differs; no claim of controlled original/new hardware speed superiority.',
 'Single default PDS per candidate, same constraints/options, no seed sweep or PLL changes. Setup/hold failures retained explicitly. Fmax is estimated, not board-verified.',
 'Actual synchronous RAM output bypass is a new data path; no bus ready -> EX/ID feedback, FIFO249x4 and one LSU preserved. Full subword bypass fails timing; LW-only refinement retains byte/halfword WB boundary.',
 'The select experiment registers identity matches only, not return data; no new data-stage latency. Added parallel data registers would normally undo the saved adjacent load-use cycle unless an existing boundary/request schedule changes.',
 'The split experiment conservatively rejects any older live slow producer before encoding, even if a younger ALU overwrites it. No independent retirement, post-ID replay or second LSU was added.',
 'JOINT_WINDOW cross is FIFO odd read-pointer starts in this round, and pop2 is consuming two words; these fields are not comparable to previous group-cross/pop-two-groups census.',
 'Fixed firmware still checks retired<=cycles when printing IPC. For >1 cases it prints unavailable; hardware counters and independent retirement counts pass, report computes retired/cycles directly. Firmware/IP images unchanged.',
 'Initial independent reference harness needed explicit function arguments and automatic functions to model broadcast changes correctly in Icarus. RTL was unchanged during reference debugging; random equivalence passed after harness repair.'
 ]));print(json.dumps({n:{k:r[k] for k in ('cycles','ipc','timing_status','estimated_fmax_mhz','estimated_peak_gain_percent','resources')} for n,r in rows.items()},indent=2))
def finish():
 copy(ROOT/'docs/dual_legacy.md',DEST/'report.md');save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
if __name__=='__main__':main()
