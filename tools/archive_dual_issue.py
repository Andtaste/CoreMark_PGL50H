"""Audit and archive the isolated dual-issue trial without promoting it."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'docs/dual_issue'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def copy(a,b):b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a,b)
def verify(x):
 for key in ('input_sha256','actual_compile_sha256'):
  for n,h in x.get(key,{}).items():
   p=ROOT/n
   if p.is_file() and sha(p)==h:continue
   snap=ROOT/'simulation/results/load_bp_dual_issue/source_snapshot'/n
   assert snap.is_file() and sha(snap)==h,(key,n,h)
def paths(report):
 text=report.read_text(errors='replace');items=[]
 for part in text.split('Startpoint  : ')[1:31]:
  m=re.search(r'Slack \(MET\)\s+(-?[\d.]+)',part);d=re.search(r'Logic:\s*([\d.]+)ns.*?Route:\s*([\d.]+)ns',part)
  start=re.search(r'\btco\b',part);data=part[start.end():part.index('Data arrival time')] if start else ''
  items.append(dict(start=part.splitlines()[0].strip(),end=re.search(r'Endpoint\s+: (.+)',part)[1].strip(),
   slack_ns=float(m[1]),logic_ns=float(d[1]),route_ns=float(d[2]),
   logic_levels=int(re.search(r'Logic Levels:\s*(\d+)',part)[1]),max_data_fanout=max(map(int,re.findall(r'net \(fanout=(\d+)\)',data)),default=0)))
 return items
def main():
 DEST.mkdir(exist_ok=True);accepted=ROOT/'docs/accepted_baseline.json';base=read(accepted)
 assert sha(accepted)=='f9266e85c40bf5a5feaa9d54f1ec77389d00a2feb02b4ed74573b5b1bc171d86'
 for n,h in base['source_sha256'].items():assert sha(ROOT/n)==h,n;copy(ROOT/n,DEST/'production_source'/n)
 sta=ROOT/'hardware/pds/report_timing/top.rtr';assert sha(sta)==sha(ROOT/'docs/ex_id_finish/validation/timing.rtr')
 copy(accepted,DEST/'accepted_baseline.json');results={}
 for name in ('dual_issue','dual_issue_finish','dual_issue_predecode'):
  src=ROOT/('simulation/results/load_bp_'+name);out=DEST/name
  g=read(src/'generation.json');sim=read(src/'result.json');val=read(src/'validation/result.json');checks=read(src/'checks/result.json');extra=read(src/'dual_checks/result.json');pds=read(src/'pds/result.json')
  for x in (sim,val,checks,extra,pds):assert x['status']=='PASS';verify(x)
  assert len(checks['tests'])==63 and len(extra['tests'])==5
  for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
  assert sim['override_sha256']==val['override_sha256']==checks['override_sha256']==extra['override_sha256']==g['override_sha256']
  assert int(sim['metrics']['Retired instructions'])==2808261
  assert int(val['metrics']['Retired instructions'])==280944
  assert sim['image_sha256']==sha(ROOT/'sw/build/coremark_performance_10/coremark.hex')
  assert val['image_sha256']==sha(ROOT/'sw/build/coremark_validation_1/coremark.hex')
  for p in src.iterdir():
   if p.is_file() and p.suffix in ('.v','.json'):copy(p,out/p.name)
  for sub in ('performance','validation','checks','dual_checks','decode_check','predecode_check','source_snapshot'):
   for p in (src/sub).rglob('*'):
    if p.is_file() and 'obj' not in p.parts and p.suffix not in ('.vvp','.elf','.bin'):copy(p,out/sub/p.relative_to(src/sub))
  for n in ('result.json','run.tcl','build.log','multiseed_summary.csv','report_timing/top.rtr','device_map/top.dmr','synthesize/apm_drm_lutram_utilization.log'):
   copy(src/'pds'/n,out/'pds'/n)
  timing=paths(src/'pds/report_timing/top.rtr');save(out/'slow_setup_paths.json',timing)
  cycles=int(sim['metrics']['Stats window cycles']);retired=int(sim['metrics']['Retired instructions']);gain=base['coremark_stats_cycles']/cycles
  results[name]=dict(cycles=cycles,retired=retired,ipc=retired/cycles,same_clock_gain_percent=(gain-1)*100,
   estimated_fmax_mhz=pds['estimated_fmax_mhz'],estimated_peak_gain_percent=(gain*pds['estimated_fmax_mhz']/base['estimated_fmax_mhz']-1)*100,
   break_even_fmax_mhz=base['estimated_fmax_mhz']/gain,resources=pds['resources'],resource_delta={k:v-base['resources'][k] for k,v in pds['resources'].items()},
   corners=pds['corners'],dual=sim['dual'],paired_instruction_percent=2*sim['dual']['secondary_retired']/retired*100,
   predictor=sim['predictor'],tests=68,extra_coverage=extra['coverage'],validation_cycles=int(val['metrics']['Stats window cycles']),slow_setup_paths=timing)
 finish=ROOT/'simulation/results/load_bp_dual_issue_finish';decode=read(finish/'decode_check/result.json');assert decode['status']=='PASS';verify(decode)
 results['dual_issue_finish']['tests']+=1
 pre=ROOT/'simulation/results/load_bp_dual_issue_predecode';precheck=read(pre/'predecode_check/result.json');assert precheck['status']=='PASS';verify(precheck)
 results['dual_issue_predecode']['tests']+=len(precheck['tests'])
 for key in ('metrics','predictor','multiply','dual'):
  assert read(ROOT/'simulation/results/load_bp_dual_issue/result.json')[key]==read(finish/'result.json')[key],key
 for key in ('metrics','predictor','multiply'):
  assert read(finish/'result.json')[key]==read(pre/'result.json')[key],key
 for key in ('secondary_retired','pairs_issued','groups_issued'):
  assert read(finish/'result.json')['dual'][key]==read(pre/'result.json')['dual'][key],key
 probe=ROOT/'simulation/results/load_bp_dual_frontend_only';x=read(probe/'result.json');assert x['status']=='PASS';verify(x)
 assert x['dual']['secondary_retired']==0
 for p in probe.iterdir():
  if p.is_file() and p.suffix in ('.v','.json'):copy(p,DEST/'frontend_only_simulation'/p.name)
 for p in (probe/'performance').iterdir():
  if p.is_file():copy(p,DEST/'frontend_only_simulation/performance'/p.name)
 control=dict(scope='Simulation only; same wide frontend, pair issuance disabled; no PDS/ISA signoff',cycles=int(x['metrics']['Stats window cycles']),ipc=2808261/int(x['metrics']['Stats window cycles']),predictor=x['predictor'],dual=x['dual'])
 profile=ROOT/'simulation/results/load_bp_dual_issue_profile';observed=read(profile/'result.json');assert observed['status']=='PASS';verify(observed)
 for key in ('metrics','predictor','multiply','dual'):assert observed[key]==read(pre/'result.json')[key],key
 assert observed['override_sha256']==read(pre/'result.json')['override_sha256']
 for p in profile.iterdir():
  if p.is_file() and p.suffix in ('.v','.json'):copy(p,DEST/'pair_profile'/p.name)
 for p in (profile/'performance').iterdir():
  if p.is_file():copy(p,DEST/'pair_profile/performance'/p.name)
 for n in ('generate_dual_issue.py','generate_dual_predecode.py','research_dual_issue.py','check_dual_issue.py','check_dual_pair_decode.py','check_dual_predecode.py','run_dual_finish.py','run_dual_predecode.py','probe_dual_frontend.py','profile_dual_issue.py','research_pds.py','archive_dual_issue.py'):copy(ROOT/'tools'/n,DEST/'tools'/n)
 for p in (ROOT/'simulation/research/dual_issue').iterdir():
  if p.is_file():copy(p,DEST/'research'/p.name)
 report=ROOT/'docs/dual_issue.md'
 if report.exists():copy(report,DEST/'report.md')
 result=dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',user_accepted=False,production_unchanged=True,baseline=base,candidates=results,frontend_only_simulation=control,pair_reasons=observed['pair_reasons'],
  accepted_sha256=sha(accepted),production_sta_sha256=sha(sta),limits=[
   'Aligned two-word groups; no cross-group pairing; second ALU source must have no live producer at ID.',
   'Eight ledger tokens now identify atomic groups; each can describe two destination registers.',
   'Two coherent copies of existing Pango TDP memories, 96 DRM versus baseline 48; no capacity increase visible to software.',
   'Two mirrored lookup ports for the same BTB64 contents, not BTB128 capacity.',
   'One PDS invocation per physical candidate; same device/options/constraints/IP/boot image; no exceptions or PLL changes.',
   '75 MHz is unchanged configured clock; Fmax and peak gain are estimates; no bitstream or board run.',
   'Short fixed CoreMark runs are diagnostic, not compliant official benchmark scores.',
   'Inherited fixed-image UART No BTB footer is stale; predictor observations show ENABLE_BP=1.'
  ])
 decision=DEST/'decision.json'
 if decision.exists():result['decision']=read(decision);result['status']=result['decision']['status']
 save(DEST/'comparison.json',result)
 save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
 print(json.dumps({k:{n:v for n,v in c.items() if n in ('cycles','ipc','estimated_fmax_mhz','estimated_peak_gain_percent','resources')} for k,c in results.items()},indent=2))
if __name__=='__main__':main()
