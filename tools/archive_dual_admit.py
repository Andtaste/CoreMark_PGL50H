"""Verify and preserve admission trials without changing either accepted baseline."""
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile
from archive_dual_issue import paths
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'docs/dual_admit'
NAMES=('dual_admit_wb','dual_admit_cross','dual_admit_both','dual_window_cross','dual_window_both')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def verify(x):
 for key in ('input_sha256','actual_compile_sha256','ip_sha256'):
  for n,h in x.get(key,{}).items():
   p=ROOT/n;assert p.is_file() and sha(p)==h,(key,n)
   if p.suffix!='.adf' and not n.replace('\\','/').startswith(('simulation/results/load_bp_dual_admit','simulation/results/load_bp_dual_window','simulation/results/dual_admit_paths','simulation/results/dual_window_paths')):copy(p,DEST/'inputs'/n)
def preserve(src,target):
 for p in src.rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(src)
  if 'obj' in rel.parts or p.suffix in ('.vvp','.elf','.bin','.o','.exe','.pyc'):continue
  if rel.parts[0]=='pds' and rel.as_posix() not in ('pds/result.json','pds/run.tcl','pds/build.log','pds/report_timing/top.rtr','pds/device_map/top.dmr','pds/place_route/top.prr','pds/synthesize/apm_drm_lutram_utilization.log'):continue
  copy(p,target/rel)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--preferred',choices=('dual_fwd_share',)+NAMES,required=True);a=ap.parse_args()
 DEST.mkdir(exist_ok=True)
 accepted=read(ROOT/'docs/accepted_dual_baseline.json');assert accepted['variant']=='dual_fwd_share' and accepted['status']=='ACCEPTED_DUAL_DEVELOPMENT_BASELINE'
 for key in ('source_sha256','evidence_sha256','ip_sha256'):
  for n,h in accepted[key].items():assert sha(ROOT/n)==h,(key,n)
 assert sha(ROOT/'docs/accepted_baseline.json')==accepted['single_issue_reference_sha256']
 assert sha(ROOT/'hardware/pds/report_timing/top.rtr')==accepted['single_issue_sta_sha256']
 prior=read(ROOT/'docs/dual_fwd/manifest.json')
 for n,h in prior.items():assert sha(ROOT/'docs/dual_fwd'/n)==h,n
 parent=ROOT/'simulation/results/load_bp_dual_fwd_share';base=read(parent/'performance/result.json');bpds=read(parent/'pds/result.json')
 profile=ROOT/'simulation/results/load_bp_dual_admit_base';x=read(profile/'performance/result.json');verify(x)
 for key in ('metrics','predictor','multiply','dual'):assert x[key]==base[key],key
 preserve(profile,DEST/'profile_baseline')
 results={}
 for name in NAMES:
  src=ROOT/('simulation/results/load_bp_'+name);g=read(src/'generation.json')
  for n,h in g['override_sha256'].items():
   assert sha(src/Path(n).name)==h,n
   if Path(n).name not in ('nc_core.v','nc_fetch.v'):assert sha(src/Path(n).name)==sha(parent/Path(n).name),n
  for p in (src/'ipcore').rglob('*'):
   if p.is_file() and p.suffix in ('.v','.idf'):assert sha(p)==sha(parent/'ipcore'/p.relative_to(src/'ipcore')),p
  for sub,count in (('checks',63),('dual_checks',7)):
   q=read(src/sub/'result.json');assert q['status']=='PASS' and len(q['tests'])==count,(name,sub);verify(q)
  audits=['admission_audit'] if name.startswith('dual_admit') else ['audit']
  for sub in audits:
   q=read(src/sub/'result.json');assert q['status']=='PASS' and len(q['tests'])>=9,(name,sub);verify(q)
  for phase in ('performance','validation'):
   q=read(src/phase/'result.json');assert q['status']=='PASS';verify(q)
   assert q['override_sha256']==g['override_sha256']
   ref=read(parent/phase/'result.json');assert q['predictor']==ref['predictor']
   for key in ('Retired instructions','Retired loads','Retired stores','BJP instructions','seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal'):
    assert q['metrics'][key]==ref['metrics'][key],(name,key)
   assert q['admission']['total']==sum(q['admission'][k] for k in ('no_second','primary','secondary','prediction','raw','waw','dependency','paired'))
  sim=read(src/'result.json');pds=read(src/'pds/result.json');assert pds['status']=='PASS' and pds['pds_exit_code']==0;verify(sim);verify(pds)
  assert sha(src/'pds/run.tcl')==pds['tcl_sha256']
  preserve(src,DEST/name);timing=paths(src/'pds/report_timing/top.rtr');save(DEST/name/'slow_setup_paths.json',timing)
  cycles=int(sim['metrics']['Stats window cycles']);gain=int(base['metrics']['Stats window cycles'])/cycles
  results[name]=dict(cycles=cycles,retired=int(sim['metrics']['Retired instructions']),ipc=int(sim['metrics']['Retired instructions'])/cycles,
   same_clock_gain_percent=(gain-1)*100,estimated_fmax_mhz=pds['estimated_fmax_mhz'],resources=pds['resources'],corners=pds['corners'],
   estimated_peak_gain_percent=(gain*pds['estimated_fmax_mhz']/bpds['estimated_fmax_mhz']-1)*100,
   break_even_fmax_mhz=bpds['estimated_fmax_mhz']/gain,dual=sim['dual'],admission=sim['admission'],slow_setup_paths=timing)
 for name in ('dual_fwd_share',)+NAMES:
  prefix='dual_window_paths' if name.startswith('dual_window') else 'dual_admit_paths';src=ROOT/'simulation/results'/prefix/name
  q=read(src/'result.json');assert q['status']=='PASS';verify(q)
  for n in ('result.json','target.tcl','build.log','wb_to_id.rtr','frontend.rtr','wb_to_f1.rtr'):copy(src/n,DEST/'targeted_paths'/name/n)
  if name in results:results[name]['targeted_paths']=q['paths']
 for name in ('dual_fwd_share',)+NAMES:
  src=ROOT/'simulation/results/dual_admit_front'/name;q=read(src/'result.json');assert q['status']=='PASS';verify(q)
  assert sha(src/'frontend.rtr')==q['report_sha256']
  for n in ('result.json','target.tcl','build.log','frontend.rtr'):copy(src/n,DEST/'all_frontend_paths'/name/n)
  if name in results:results[name]['all_frontend_paths']=q['paths']
 with zipfile.ZipFile(DEST/'routed_snapshots.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
  for name in ('dual_fwd_share',)+NAMES:
   for file in ('top_pnr.adf','top_pnr.netlist'):
    p=ROOT/('simulation/results/load_bp_'+name+'/pds/place_route/'+file);z.write(p,name+'/'+file)
 for file in ('generate_dual_admit.py','run_dual_admit.py','profile_dual_admit.py','check_dual_admit_extra.py','audit_dual_admit.py','report_dual_admit.py','generate_dual_window.py','run_dual_window.py','audit_dual_window.py','report_dual_window.py','archive_dual_admit.py','report_dual_front.py','research_dual_issue.py','research_dual_ram_pds.py','audit_dual_ram.py','archive_dual_issue.py'):
  copy(ROOT/'tools'/file,DEST/'tools'/file)
 for file in ('nc_fetch.v','nc_core.v'):copy(parent/file,DEST/'parent'/file)
 copy(ROOT/'docs/dual_admit.md',DEST/'report.md');copy(ROOT/'docs/accepted_dual_baseline.json',DEST/'accepted_dual_baseline.json')
 save(DEST/'comparison.json',dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',preferred_research_candidate=a.preferred,accepted_dual_unchanged=True,
  baseline_pds=bpds,baseline_profile=x['admission'],candidates=results,parent_archive_verified_files=len(prior),
  limits=['One completed PDS implementation per physical candidate; same options/constraints/PLL/images; no seed sweep.',
   'Base-profile simulation source is byte-identical to accepted dual; local measurement counters are bench-only.',
   'All trials retain two ALUs, one LSU, four fetch groups, eight ledger groups and the original ID/EX/MEM/WB boundaries.',
   'Only registered WB data can feed new secondary ID forwarding; no current EX-to-ID, EX0-to-EX1 or raw-RAM-to-EX bypass.',
   'Cross pairing requires a clean high-word fall-through head and a clean following two-word group; not unrestricted cross-group issue.',
   'Frontend/RF random simulation: 300000 cycles and 2400000 RF read checks per candidate, plus 63 core regressions, fault cancellation and two CoreMark images; not full sequential formal proof.',
   'WB-only combinational admission/data equations SAT checked for WB-enabled candidates; no whole-core formal claim.',
   'Window variants retain 24 new Verilator SIDEEFFECT and 4 new unused-input-field warnings; no latch/cycle/multi-driver warnings. These trials are not lint-clean and are not recommended for integration.',
   'Legacy harness scope text says aligned; actual cross-group behavior is specified by generation scope, RTL and cross_pairs counters.',
   'Fmax is estimated and CoreMark is a short diagnostic; PLL remains approximately 75 MHz, no board/Flash/game validation.',
   'Initial simulation-report decoding failed due to WSL output encoding; completed simulations were reused after parser repair with explicit result flag. Window initial SV keyword compile error was fixed before simulation/PDS; initial diagnostics retained.']))
 save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
 print(json.dumps({k:{n:v for n,v in x.items() if n in ('cycles','ipc','estimated_fmax_mhz','same_clock_gain_percent','estimated_peak_gain_percent','resources')} for k,x in results.items()},indent=2))
if __name__=='__main__':main()
