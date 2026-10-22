"""Freeze native FIFO/registered forwarding trials and verify both accepted baselines."""
from pathlib import Path
import hashlib,json,shutil,zipfile
from archive_dual_issue import paths
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'docs/dual_native'
NAMES=tuple('dual_native_'+v for v in ('fifo','select','forward','both'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def verify(x):
 for key in ('input_sha256','actual_compile_sha256','ip_sha256','canonical_sha256'):
  for n,h in x.get(key,{}).items():
   p=ROOT/n;assert sha(p)==h,(key,n)
   if p.suffix!='.adf' and not n.replace('\\','/').startswith('simulation/results/load_bp_dual_native'):
    copy(p,DEST/'inputs'/n)
def preserve(src,dest):
 for p in src.rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(src)
  if 'obj' in rel.parts or p.suffix in ('.vvp','.elf','.bin','.o','.exe','.pyc'):continue
  if rel.parts[0]=='pds' and rel.as_posix() not in ('pds/result.json','pds/run.tcl','pds/build.log','pds/report_timing/top.rtr','pds/device_map/top.dmr','pds/place_route/top.prr','pds/synthesize/apm_drm_lutram_utilization.log'):continue
  copy(p,dest/rel)
def main():
 DEST.mkdir(exist_ok=True)
 accepted=read(ROOT/'docs/accepted_dual_baseline.json');assert accepted['variant']=='dual_fwd_share'
 for key in ('source_sha256','evidence_sha256','ip_sha256'):
  for n,h in accepted[key].items():assert sha(ROOT/n)==h,(key,n)
 assert sha(ROOT/'docs/accepted_baseline.json')==accepted['single_issue_reference_sha256']
 assert sha(ROOT/'hardware/pds/report_timing/top.rtr')==accepted['single_issue_sta_sha256']
 single=read(ROOT/'docs/accepted_baseline.json')
 for n,h in single['source_sha256'].items():assert sha(ROOT/n)==h,n
 prior={}
 for name in ('dual_fwd','dual_fan','dual_admit'):
  m=read(ROOT/'docs'/name/'manifest.json')
  for n,h in m.items():assert sha(ROOT/'docs'/name/n)==h,(name,n)
  prior[name]=len(m)
 parent=ROOT/'simulation/results/load_bp_dual_fwd_share';base=read(parent/'performance/result.json');bpds=read(parent/'pds/result.json')
 results={}
 for name in NAMES:
  src=ROOT/('simulation/results/load_bp_'+name);g=read(src/'generation.json');verify(g)
  assert sha(ROOT/'tools/generate_dual_native.py')==g['generator_sha256']
  for n,h in g['override_sha256'].items():
   assert sha(src/Path(n).name)==h,n
   if Path(n).name not in ('nc_core.v','nc_fetch.v','nc_operands.v','nc_mul_pipeline.v'):assert sha(src/Path(n).name)==sha(parent/Path(n).name),n
  for p in (src/'ipcore').rglob('*'):
   if p.is_file() and p.suffix in ('.v','.idf'):assert sha(p)==sha(parent/'ipcore'/p.relative_to(src/'ipcore')),p
  for sub,count in (('checks',63),('dual_checks',7),('audit',5)):
   q=read(src/sub/'result.json');assert q['status']=='PASS' and len(q['tests'])==count,(name,sub);verify(q)
  for phase in ('performance','validation'):
   q=read(src/phase/'result.json');assert q['status']=='PASS';verify(q);assert q['override_sha256']==g['override_sha256']
   ref=read(parent/phase/'result.json');assert q['predictor']==ref['predictor']
   for k in ('Retired instructions','Retired loads','Retired stores','BJP instructions','seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal'):assert q['metrics'][k]==ref['metrics'][k],(name,k)
  sim=read(src/'result.json');pds=read(src/'pds/result.json');assert pds['status'] in ('PASS','TIMING_FAILED') and pds['pds_exit_code']==0;verify(sim);verify(pds)
  assert sha(src/'pds/run.tcl')==pds['tcl_sha256']
  preserve(src,DEST/name);timing=paths(src/'pds/report_timing/top.rtr');save(DEST/name/'slow_setup_paths.json',timing)
  cycles=int(sim['metrics']['Stats window cycles']);gain=int(base['metrics']['Stats window cycles'])/cycles
  target=ROOT/'simulation/results/dual_native_paths'/name;q=read(target/'result.json');verify(q)
  for n,h in q['report_sha256'].items():assert sha(target/n)==h,n
  preserve(target,DEST/'targeted_paths'/name)
  results[name]=dict(cycles=cycles,retired=int(sim['metrics']['Retired instructions']),ipc=int(sim['metrics']['Retired instructions'])/cycles,
   same_clock_gain_percent=(gain-1)*100,estimated_fmax_mhz=pds['estimated_fmax_mhz'],timing_status=pds['status'],resources=pds['resources'],corners=pds['corners'],
   estimated_peak_gain_percent=(gain*pds['estimated_fmax_mhz']/bpds['estimated_fmax_mhz']-1)*100,
   break_even_fmax_mhz=bpds['estimated_fmax_mhz']/gain,dual=sim['dual'],admission=sim['admission'],slow_setup_paths=timing,targeted_paths=q['paths'])
 for sub in ('forwarding_equivalence','protocol'):
  q=read(ROOT/'simulation/results/load_bp_dual_native_both'/sub/'result.json');assert q['status']=='PASS';verify(q)
 selector_dir=ROOT/'simulation/results/dual_native_selectors';selectors=read(selector_dir/'result.json');assert selectors['status']=='PASS';verify(selectors)
 for n,h in selectors['report_sha256'].items():assert sha(selector_dir/n)==h,n
 preserve(selector_dir,DEST/'selector_paths')
 # The selector-only control must preserve the entire accepted cycle profile.
 q=read(ROOT/'simulation/results/load_bp_dual_native_select/performance/result.json')
 for k in ('metrics','dual','predictor','multiply'):assert q[k]==base[k],k
 with zipfile.ZipFile(DEST/'routed_snapshots.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
  for name in NAMES:
   for f in ('top_pnr.adf','top_pnr.netlist'):z.write(ROOT/('simulation/results/load_bp_'+name+'/pds/place_route/'+f),name+'/'+f)
 snapshot_hashes={}
 with zipfile.ZipFile(DEST/'routed_snapshots.zip') as z:
  for name in NAMES:
   for f in ('top_pnr.adf','top_pnr.netlist'):
    n=name+'/'+f;h=sha(ROOT/('simulation/results/load_bp_'+name+'/pds/place_route/'+f));assert hashlib.sha256(z.read(n)).hexdigest()==h;snapshot_hashes[n]=h
 save(DEST/'routed_content_sha256.json',snapshot_hashes)
 for p in (ROOT/'tools').glob('*dual_native*.py'):copy(p,DEST/'tools'/p.name)
 for n in ('research_dual_issue.py','research_dual_ram_pds.py','audit_dual_ram.py','archive_dual_issue.py'):copy(ROOT/'tools'/n,DEST/'tools'/n)
 for n in ('nc_fetch.v','nc_core.v','nc_operands.v'):copy(parent/n,DEST/'parent'/n)
 copy(ROOT/'docs/accepted_dual_baseline.json',DEST/'accepted_dual_baseline.json')
 eligible=[(v['estimated_peak_gain_percent'],n) for n,v in results.items() if v['timing_status']=='PASS' and v['estimated_peak_gain_percent']>0]
 preferred=max(eligible)[1] if eligible else 'dual_fwd_share'
 save(DEST/'comparison.json',dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',preferred_research_candidate=preferred,accepted_dual_unchanged=True,baseline_pds=bpds,candidates=results,selector_paths=selectors['paths'],prior_archive_verified_files=prior,
  limits=['One PDS implementation per candidate, same options/constraints/PLL/firmware; no seed sweep.',
   'Two ALUs, one LSU; slow load/MUL/DIV side dependencies still split; same-pair RAW/WAW still prohibited.',
   'Native FIFO has eight instruction slots, two registered heads, prepared adjacency and two parity banks; old aligned group frontend retained in forwarding-only control.',
   'Future producer identity only is compared before the selector register. Source valid/data are registered; no current EX or raw RAM data forwarded directly to ID/EX.',
   'No whole-CPU sequential formal proof. Random reference-queue comparison covers 300000 cycles; actual CPU future-tag protocol separately checked in eight differential runs.',
   'Initial standalone queue coverage threshold expected >1000 insertion hits; four-operand random traffic produced 640-693. Initial diagnostic retained; final thresholds require >=300 and measured counts are reported.',
   'First two performance runs were repeated solely to record the finalized wrapper metadata/provenance; cycle profiles were identical.',
   'Fmax is a routed estimate; CoreMark is short diagnostic, PLL remains ~75 MHz. No board, Flash, or game measurement.']))
 print(json.dumps({k:{n:v for n,v in x.items() if n in ('cycles','ipc','estimated_fmax_mhz','timing_status','same_clock_gain_percent','estimated_peak_gain_percent','resources')} for k,x in results.items()},indent=2))
def finish_manifest():
 copy(ROOT/'docs/dual_native.md',DEST/'report.md')
 save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
if __name__=='__main__':main();finish_manifest()
