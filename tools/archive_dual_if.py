"""Verify and archive isolated IF classification timing experiments."""
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile
from archive_dual_issue import paths
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'docs/dual_if'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def copy(a,b):b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a,b)
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def verify(x):
 for key in ('input_sha256','actual_compile_sha256','ip_sha256'):
  for n,h in x.get(key,{}).items():
   p=ROOT/n;assert p.is_file() and sha(p)==h,(key,n)
   if p.suffix!='.adf' and not n.replace('\\','/').startswith(('simulation/results/load_bp_dual_if','simulation/results/dual_if_paths')):
    copy(p,DEST/'inputs'/n)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--preferred',choices=('dual_ram_logic','dual_if_class','dual_if_parts'),required=True);a=ap.parse_args()
 DEST.mkdir(exist_ok=True);parent=ROOT/'simulation/results/load_bp_dual_ram_logic';base=read(ROOT/'docs/accepted_baseline.json')
 assert base['status']=='ACCEPTED' and sha(ROOT/'docs/accepted_baseline.json')=='f9266e85c40bf5a5feaa9d54f1ec77389d00a2feb02b4ed74573b5b1bc171d86'
 for n,h in base['source_sha256'].items():assert sha(ROOT/n)==h,n
 assert sha(ROOT/'hardware/pds/report_timing/top.rtr')=='047c7504f1f3967d2499de007e44faa87013cebec03c94b941682521c12794d9'
 previous={}
 for folder in ('dual_ram','dual_bus'):
  m=read(ROOT/'docs'/folder/'manifest.json')
  for n,h in m.items():assert sha(ROOT/'docs'/folder/n)==h,(folder,n)
  previous[folder]=len(m)
 results={};parent_pds=read(parent/'pds/result.json')
 for name in ('dual_if_class','dual_if_parts'):
  src=ROOT/('simulation/results/load_bp_'+name);meta=read(src/'generation.json')
  for n,h in meta['override_sha256'].items():
   assert sha(src/Path(n).name)==h,n
   if Path(n).name!='nc_fetch.v':assert sha(src/Path(n).name)==sha(parent/Path(n).name),n
  tail=' always @(posedge clk or negedge rst_n) begin'
  assert (src/'nc_fetch.v').read_text().split(tail)[1]==(parent/'nc_fetch.v').read_text().split(tail)[1]
  for p in (src/'ipcore').rglob('*'):
   if p.is_file() and p.suffix in ('.v','.idf'):assert sha(p)==sha(parent/'ipcore'/p.relative_to(src/'ipcore')),p
  for sub,count in {'checks':63,'dual_checks':5,'audit':5,'classification':2,'frontend_equivalence':1}.items():
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
  gain=base['coremark_stats_cycles']/int(sim['metrics']['Stats window cycles'])
  results[name]=dict(estimated_fmax_mhz=pds['estimated_fmax_mhz'],resources=pds['resources'],corners=pds['corners'],slow_setup_paths=timing,
   cycle_count=int(sim['metrics']['Stats window cycles']),ipc=int(sim['metrics']['Retired instructions'])/int(sim['metrics']['Stats window cycles']),
   fmax_change_vs_parent_percent=(pds['estimated_fmax_mhz']/parent_pds['estimated_fmax_mhz']-1)*100,
   estimated_peak_gain_vs_accepted_percent=(gain*pds['estimated_fmax_mhz']/base['estimated_fmax_mhz']-1)*100)
 for name in ('dual_ram_logic','dual_if_class','dual_if_parts'):
  src=ROOT/'simulation/results/dual_if_paths'/name;x=read(src/'result.json');assert x['status']=='PASS';verify(x)
  for n in ('result.json','target.tcl','build.log','incoming.rtr','consumer.rtr'):copy(src/n,DEST/'targeted_paths'/name/n)
  if name in results:results[name]['targeted_paths']={k:v[0] for k,v in x['paths'].items()}
 with zipfile.ZipFile(DEST/'routed_snapshots.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
  for name in ('dual_ram_logic','dual_if_class','dual_if_parts'):
   p=ROOT/('simulation/results/load_bp_'+name+'/pds/place_route/top_pnr.adf');z.write(p,name+'/top_pnr.adf')
 for n in ('generate_dual_if.py','run_dual_if.py','check_dual_if.py','check_dual_if_frontend.py','report_dual_if_paths.py','archive_dual_if.py','audit_dual_ram.py','research_dual_ram_pds.py','research_dual_issue.py','check_dual_ram.py','archive_dual_issue.py'):
  copy(ROOT/'tools'/n,DEST/'tools'/n)
 copy(ROOT/'simulation/research/dual_ram/if_class_equivalence_tb.v',DEST/'research/if_class_equivalence_tb.v')
 copy(ROOT/'docs/dual_if.md',DEST/'report.md');copy(ROOT/'docs/accepted_baseline.json',DEST/'accepted_baseline.json')
 save(DEST/'comparison.json',dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',preferred_research_candidate=a.preferred,user_accepted=False,production_unchanged=True,
  parent_pds=parent_pds,parent_targeted_paths=read(ROOT/'simulation/results/dual_if_paths/dual_ram_logic/result.json')['paths'],
  candidates=results,previous_archive_verified_files=previous,
  limits=['One PDS invocation per candidate; identical clock constraints, PLL and images; no new cycle or seed sweep.',
   'All five flags SAT-equivalent for every binary 32-bit instruction. Sequential frontend ownership checked by simulation, not whole-core formal proof.',
   'Only nc_fetch.v differs from the parent core/SoC overrides; bus-only candidates from the previous round are not included.',
   'Partial predicates add final OR logic after IF registers; consumer timing is measured explicitly.',
   'Production remains the accepted single-issue core; short CoreMark is diagnostic and Fmax is an estimate.']))
 retention=DEST/'retention.json'
 if retention.exists():
  decision=read(retention);assert decision['variant']==a.preferred
  x=read(DEST/'comparison.json');x.update(status=decision['status'],user_retained=True,retention=decision)
  save(DEST/'comparison.json',x)
 audit=DEST/'resource_audit/result.json'
 if audit.exists():
  x=read(audit);assert x['status']=='PASS'
  for n,h in x['input_sha256'].items():assert sha(ROOT/n)==h,n
  copy(ROOT/'tools/audit_dual_if_resources.py',DEST/'tools/audit_dual_if_resources.py')
 save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
 print(json.dumps({k:{n:v for n,v in x.items() if n in ('estimated_fmax_mhz','resources','fmax_change_vs_parent_percent','targeted_paths','estimated_peak_gain_vs_accepted_percent')} for k,x in results.items()},indent=2))
if __name__=='__main__':main()
