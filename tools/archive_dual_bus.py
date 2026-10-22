"""Audit bus timing trials and preserve measured regressions without promotion."""
from pathlib import Path
import hashlib,json,shutil,zipfile
from archive_dual_issue import paths
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'docs/dual_bus'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def copy(a,b):b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a,b)
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def verify(x):
 for key in ('input_sha256','actual_compile_sha256','ip_sha256'):
  for n,h in x.get(key,{}).items():
   p=ROOT/n;assert p.is_file() and sha(p)==h,(key,n)
   if p.suffix!='.adf' and not n.replace('\\','/').startswith(('simulation/results/load_bp_dual_bus','simulation/results/dual_bus_paths')):
    copy(p,DEST/'inputs'/n)
def main():
 DEST.mkdir(exist_ok=True);parent=ROOT/'simulation/results/load_bp_dual_ram_logic'
 base=read(ROOT/'docs/accepted_baseline.json');assert base['status']=='ACCEPTED'
 assert sha(ROOT/'docs/accepted_baseline.json')=='f9266e85c40bf5a5feaa9d54f1ec77389d00a2feb02b4ed74573b5b1bc171d86'
 for n,h in base['source_sha256'].items():assert sha(ROOT/n)==h,n
 assert sha(ROOT/'hardware/pds/report_timing/top.rtr')=='047c7504f1f3967d2499de007e44faa87013cebec03c94b941682521c12794d9'
 previous=read(ROOT/'docs/dual_ram/manifest.json')
 for n,h in previous.items():assert sha(ROOT/'docs/dual_ram'/n)==h,n
 results={}
 for name in ('dual_bus_split','dual_bus_local'):
  src=ROOT/('simulation/results/load_bp_'+name);meta=read(src/'generation.json')
  for n,h in meta['override_sha256'].items():
   assert sha(src/Path(n).name)==h,n
   if Path(n).name!='nc_local_bus.v':assert sha(src/Path(n).name)==sha(parent/Path(n).name),n
  for p in (src/'ipcore').rglob('*'):
   if p.is_file() and p.suffix in ('.v','.idf'):assert sha(p)==sha(parent/'ipcore'/p.relative_to(src/'ipcore')),p
  counts={'checks':63,'dual_checks':5,'audit':5,'bus_equivalence':2,'bus_formal':1}
  for sub,count in counts.items():
   x=read(src/sub/'result.json');assert x['status']=='PASS' and len(x['tests'])==count,(name,sub);verify(x)
  for phase in ('performance','validation'):
   x=read(src/phase/'result.json');assert x['status']=='PASS';verify(x);prior=read(parent/phase/'result.json')
   for key in ('metrics','predictor','multiply','dual'):assert x[key]==prior[key],(name,phase,key)
  sim=read(src/'result.json');pds=read(src/'pds/result.json');assert pds['status']=='PASS';verify(sim);verify(pds)
  assert sha(src/'pds/run.tcl')==pds['tcl_sha256'] and pds['pds_exit_code']==0
  for p in src.rglob('*'):
   if not p.is_file() or 'obj' in p.relative_to(src).parts:continue
   rel=p.relative_to(src)
   if rel.parts[0]=='pds':
    if rel.as_posix() not in ('pds/result.json','pds/run.tcl','pds/build.log','pds/report_timing/top.rtr','pds/device_map/top.dmr','pds/synthesize/apm_drm_lutram_utilization.log'):continue
   elif p.suffix in ('.vvp','.elf','.bin','.o','.exe','.pyc'):continue
   copy(p,DEST/name/rel)
  timing=paths(src/'pds/report_timing/top.rtr');save(DEST/name/'slow_setup_paths.json',timing)
  results[name]=dict(estimated_fmax_mhz=pds['estimated_fmax_mhz'],resources=pds['resources'],corners=pds['corners'],slow_setup_paths=timing,
   cycle_count=int(sim['metrics']['Stats window cycles']),ipc=int(sim['metrics']['Retired instructions'])/int(sim['metrics']['Stats window cycles']),
   fmax_change_vs_parent_percent=(pds['estimated_fmax_mhz']/read(parent/'pds/result.json')['estimated_fmax_mhz']-1)*100)
 for name in ('dual_ram_logic','dual_bus_split','dual_bus_local'):
  src=ROOT/'simulation/results/dual_bus_paths'/name;x=read(src/'result.json');assert x['status']=='PASS';verify(x)
  for n in ('result.json','target.tcl','build.log','report_timing/top.rtr'):copy(src/n,DEST/'targeted_paths'/name/n)
  if name in results:results[name]['targeted_pointer_to_ram_ce']=x['slow_setup_paths'][0]
 # Preserve the actual routed snapshots used by the targeted reports;
 # re-running PNR is not a substitute for an identical routed input.
 snapshots=DEST/'routed_snapshots.zip'
 with zipfile.ZipFile(snapshots,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for name in ('dual_ram_logic','dual_bus_split','dual_bus_local'):
   p=ROOT/('simulation/results/load_bp_'+name+'/pds/place_route/top_pnr.adf');z.write(p,name+'/top_pnr.adf')
 for n in ('generate_dual_bus.py','run_dual_bus.py','check_dual_bus.py','prove_dual_bus.py','report_dual_bus_path.py','archive_dual_bus.py','audit_dual_ram.py','research_dual_ram_pds.py','research_dual_issue.py','check_dual_ram.py','archive_dual_issue.py'):
  copy(ROOT/'tools'/n,DEST/'tools'/n)
 copy(ROOT/'simulation/research/dual_ram/bus_equivalence_tb.v',DEST/'research/bus_equivalence_tb.v')
 copy(ROOT/'docs/dual_bus.md',DEST/'report.md');copy(ROOT/'docs/accepted_baseline.json',DEST/'accepted_baseline.json')
 save(DEST/'comparison.json',dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',recommendation='KEEP_PARENT_DUAL_RAM_LOGIC',production_unchanged=True,
  parent_pds=read(parent/'pds/result.json'),parent_targeted_path=read(ROOT/'simulation/results/dual_bus_paths/dual_ram_logic/result.json')['slow_setup_paths'][0],
  candidates=results,previous_archive_verified_files=len(previous),
  limits=['One PDS invocation per candidate; no constraint/PLL change, stage added, or seed sweep.',
   'Combinational SAT proof is limited to bus acceptance and RAM enable cones; sequential checks are simulation, not whole-core formal proof.',
   'IP and every core/frontend RTL source are byte-identical to parent except nc_local_bus.v; parent vendor-IP initialization checks remain applicable.',
   'The control path is shortened, not cut by a new register. FIFO read-pointer fanout remains.',
   'Both candidates lose whole-core Fmax; no adoption is recommended from local path improvement alone.']))
 save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
 print(json.dumps({k:{n:v for n,v in x.items() if n in ('estimated_fmax_mhz','resources','fmax_change_vs_parent_percent','targeted_pointer_to_ram_ce')} for k,x in results.items()},indent=2))
if __name__=='__main__':main()
