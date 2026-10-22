"""Preserve isolated FIFO fanout experiments and the retained parent."""
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile
from archive_dual_issue import paths
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'docs/dual_fan'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def copy(a,b):b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a,b)
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def verify(x):
 for key in ('input_sha256','actual_compile_sha256','ip_sha256'):
  for n,h in x.get(key,{}).items():
   p=ROOT/n;assert p.is_file() and sha(p)==h,(key,n)
   if p.suffix!='.adf' and not n.replace('\\','/').startswith(('simulation/results/load_bp_dual_fan','simulation/results/dual_fan_paths')):copy(p,DEST/'inputs'/n)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--preferred',choices=('dual_if_parts','dual_fan_guide','dual_fan_banks'),required=True);a=ap.parse_args()
 DEST.mkdir(exist_ok=True);parent=ROOT/'simulation/results/load_bp_dual_if_parts';base=read(ROOT/'docs/accepted_baseline.json')
 assert sha(ROOT/'docs/accepted_baseline.json')=='f9266e85c40bf5a5feaa9d54f1ec77389d00a2feb02b4ed74573b5b1bc171d86'
 for n,h in base['source_sha256'].items():assert sha(ROOT/n)==h,n
 assert sha(ROOT/'hardware/pds/report_timing/top.rtr')=='047c7504f1f3967d2499de007e44faa87013cebec03c94b941682521c12794d9'
 old=read(ROOT/'docs/dual_if/manifest.json')
 for n,h in old.items():assert sha(ROOT/'docs/dual_if'/n)==h,n
 assert read(ROOT/'docs/dual_if/retention.json')['variant']=='dual_if_parts'
 parent_pds=read(parent/'pds/result.json');results={}
 for name in ('dual_fan_guide','dual_fan_banks'):
  src=ROOT/('simulation/results/load_bp_'+name);meta=read(src/'generation.json')
  for n,h in meta['override_sha256'].items():
   assert sha(src/Path(n).name)==h,n
   if Path(n).name!='nc_fifo.v':assert sha(src/Path(n).name)==sha(parent/Path(n).name),n
  for p in (src/'ipcore').rglob('*'):
   if p.is_file() and p.suffix in ('.v','.idf'):assert sha(p)==sha(parent/'ipcore'/p.relative_to(src/'ipcore')),p
  for sub,count in {'checks':63,'dual_checks':5,'audit':5,'fifo_equivalence':3}.items():
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
    if rel.as_posix() not in ('pds/result.json','pds/run.tcl','pds/build.log','pds/report_timing/top.rtr','pds/device_map/top.dmr','pds/place_route/top.prr','pds/synthesize/apm_drm_lutram_utilization.log'):continue
   elif rel.parts[0]=='pds_interrupted':
    if p.name not in ('run.log','run.tcl','build.log'):continue
   elif p.suffix in ('.vvp','.elf','.bin','.o','.exe','.pyc'):continue
   copy(p,DEST/name/rel)
  timing=paths(src/'pds/report_timing/top.rtr');save(DEST/name/'slow_setup_paths.json',timing)
  gain=base['coremark_stats_cycles']/int(sim['metrics']['Stats window cycles'])
  results[name]=dict(estimated_fmax_mhz=pds['estimated_fmax_mhz'],resources=pds['resources'],corners=pds['corners'],slow_setup_paths=timing,
   cycle_count=int(sim['metrics']['Stats window cycles']),ipc=int(sim['metrics']['Retired instructions'])/int(sim['metrics']['Stats window cycles']),
   fmax_change_vs_parent_percent=(pds['estimated_fmax_mhz']/parent_pds['estimated_fmax_mhz']-1)*100,
   estimated_peak_gain_vs_accepted_percent=(gain*pds['estimated_fmax_mhz']/base['estimated_fmax_mhz']-1)*100)
 for name in ('dual_if_parts','dual_fan_guide','dual_fan_banks'):
  src=ROOT/'simulation/results/dual_fan_paths'/name;x=read(src/'result.json');assert x['status']=='PASS';verify(x)
  for n in ('result.json','target.tcl','build.log','rd.rtr','wr.rtr'):copy(src/n,DEST/'targeted_paths'/name/n)
  if name in results:results[name]['pointer_evidence']={k:v for k,v in x.items() if k in ('pointer_instance_count','pointer_instances','observed_pointer_fanout','distributed_ram')}
 with zipfile.ZipFile(DEST/'routed_snapshots.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
  for name in ('dual_if_parts','dual_fan_guide','dual_fan_banks'):
   for file in ('top_pnr.adf','top_pnr.netlist'):
    p=ROOT/('simulation/results/load_bp_'+name+'/pds/place_route/'+file);z.write(p,name+'/'+file)
 for n in ('generate_dual_fan.py','run_dual_fan.py','check_dual_fan.py','report_dual_fan.py','archive_dual_fan.py','audit_dual_ram.py','research_dual_ram_pds.py','research_dual_issue.py','check_dual_ram.py','archive_dual_issue.py'):copy(ROOT/'tools'/n,DEST/'tools'/n)
 copy(ROOT/'simulation/research/dual_ram/fan_fifo_tb.v',DEST/'research/fan_fifo_tb.v');copy(ROOT/'docs/dual_fan.md',DEST/'report.md')
 copy(ROOT/'docs/accepted_baseline.json',DEST/'accepted_baseline.json')
 save(DEST/'comparison.json',dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',preferred_research_candidate=a.preferred,production_unchanged=True,
  parent_pds=parent_pds,candidates=results,retained_parent_manifest_files=len(old),
  limits=['FIFO-only trials; core, frontend, IP and issue policy are byte-identical to retained parent.',
   'One completed PDS run per candidate; first attempts were interrupted before completion and their logs are preserved separately.',
   'FIFO scoreboard covers 300000 cycles/600000 edge checks per candidate; simulation is not a complete sequential formal proof.',
   'Pointer fanouts are measured only for drivers appearing in targeted STA reports; preservation attributes are not assumed to guarantee routed replication.',
   'No new cycle, depth change, read-through path or output-ready to input-credit path; production remains accepted single issue.']))
 save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
 print(json.dumps({k:{n:v for n,v in x.items() if n in ('estimated_fmax_mhz','resources','fmax_change_vs_parent_percent','pointer_evidence')} for k,x in results.items()},indent=2))
if __name__=='__main__':main()
