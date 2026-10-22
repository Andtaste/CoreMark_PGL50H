"""Freeze multiplier handoff trials and unchanged-RTL pairing observations."""
from pathlib import Path
import hashlib,json,re,shutil,zipfile
from parse_dual_joint_timing import paths
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'docs/dual_mul_tail'
NAMES=['dual_boundary_'+n for n in ('mulprobe','pairprobe','multail','mullowtail')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def main():
 assert not (DEST/'manifest.json').exists();DEST.mkdir(exist_ok=True);accepted=ROOT/'docs/accepted_dual_baseline.json';a=read(accepted);assert a['variant']=='dual_boundary_storewrite'
 for k in ('source_sha256','ip_sha256','evidence_sha256'):
  for n,h in a[k].items():assert sha(ROOT/n)==h,(k,n)
 for k,n in (('single_issue_reference_sha256','docs/accepted_baseline.json'),('single_issue_sta_sha256','hardware/pds/report_timing/top.rtr')):assert sha(ROOT/n)==a[k]
 prior={}
 for name in ('dual_store_simple','dual_store_simple_adoption','dual_mem_ipc','dual_timing80'):
  d=ROOT/'docs'/name;m=read(d/'manifest.json')
  for n,h in m.items():assert sha(d/n)==h,(name,n)
  prior[name]=len(m)
 def verify(x,label):
  for k in ('input_sha256','actual_compile_sha256','ip_sha256'):
   for n,h in x.get(k,{}).items():
    p=ROOT/n
    if not p.exists() and n.replace('\\','/').startswith('tmp/'):p=ROOT.parent/n
    assert p.is_file() and sha(p)==h,(label,n)
    if not any(('load_bp_'+v) in n for v in NAMES) and p.suffix!='.adf':copy(p,DEST/'inputs'/n)
 rows={}
 for name in NAMES:
  src=ROOT/('simulation/results/load_bp_'+name);g=read(src/'generation.json');verify(g,name);assert g['accepted_dual_sha256']==sha(accepted)
  gen=ROOT/('tools/generate_dual_pair_probe.py' if name.endswith('pairprobe') else 'tools/generate_dual_mul_tail.py');assert sha(gen)==g['generator_sha256']
  for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
  statuses={}
  for p in src.rglob('result.json'):
   if 'obj' in p.parts:continue
   x=read(p);verify(x,str(p))
   if p.parent.name!='pds':assert x['status']=='PASS',p
   statuses[str(p.parent.relative_to(src))]=dict(status=x['status'],tests=len(x.get('tests',[])))
  sim=read(src/'performance/result.json');row={k:sim[k] for k in ('metrics','predictor','multiply','dual','joint','boundary','mem_ipc','load_queue','mul_tail','pair_reject','pair_supply','pair_census','pair_expand')};row['checks']=statuses;row['ipc']=int(sim['metrics']['Retired instructions'])/int(sim['metrics']['Stats window cycles'])
  if name.endswith('pairprobe'):row.update(pair_detail=sim['pair_detail'],pair_single_lsu=sim['pair_single_lsu'])
  if name.endswith(('multail','mullowtail')):
   for sub,count in (('checks',63),('pair_checks',6),('cancel_checks',4),('audit_checks',4),('timeline_checks',4),('protocol',8),('mul_protocol',4),('mul_unit',3),('posted_soc_final',6)):assert statuses[sub]['tests']==count,(name,sub,statuses.get(sub))
   assert statuses['uart80']['status']=='PASS' and read(src/'mul_unit/result.json')['cycles']==90000
   pd=read(src/'pds/result.json');assert pd['pds_exit_code']==0 and sha(src/'pds/run.tcl')==pd['tcl_sha256'];assert re.search(r'12\.500\s+\{0 6\.25\}',(src/'pds/report_timing/top.rtr').read_text(errors='replace'))
   row.update(timing_status=pd['status'],estimated_fmax_mhz=pd['estimated_fmax_mhz'],resources=pd['resources'],corners=pd['corners'],global_paths=paths(src/'pds/report_timing/top.rtr'),selected_paths=read(src/'mul_paths/result.json')['paths'])
   snaps=[src/'pds/place_route/top_pnr.adf',src/'pds/synthesize/top_syn.vm'];assert all(p.exists() for p in snaps);z=DEST/name/'routed_snapshot.zip';z.parent.mkdir(parents=True,exist_ok=True)
   with zipfile.ZipFile(z,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for p in snaps:archive.write(p,p.relative_to(src).as_posix())
   with zipfile.ZipFile(z) as archive:
    for p in snaps:assert hashlib.sha256(archive.read(p.relative_to(src).as_posix())).hexdigest()==sha(p)
   row['routed_snapshot_sha256']={str(p.relative_to(src)):sha(p) for p in snaps}
  rows[name]=row
  for p in src.rglob('*'):
   if not p.is_file():continue
   rel=p.relative_to(src)
   if 'obj' in rel.parts or p.suffix in ('.vvp','.o','.exe','.pyc','.elf','.bin'):continue
   if rel.parts[0]=='pds' and rel.as_posix() not in ('pds/result.json','pds/run.tcl','pds/build.log','pds/report_timing/top.rtr','pds/device_map/top.dmr','pds/place_route/top.prr','pds/synthesize/apm_drm_lutram_utilization.log'):continue
   if rel.parts[0]=='mul_paths' and len(rel.parts)>2:continue
   copy(p,DEST/name/rel)
 verified=ROOT/'simulation/results/dual_mul_tail_verify';verify(read(verified/'result.json'),'regeneration');assert read(verified/'result.json')['status']=='PASS'
 for p in verified.rglob('*'):
  if p.is_file():copy(p,DEST/'verification'/p.relative_to(verified))
 preferred=max((n for n in NAMES if rows[n].get('timing_status')=='PASS'),key=lambda n:rows[n]['estimated_fmax_mhz'],default=None)
 save(DEST/'comparison.json',dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',preferred_candidate=preferred,accepted_descriptor_sha256=sha(accepted),accepted=a,candidates=rows,prior_archive_verified_files=prior,note='Only multiplier source changed in candidates; no pairing admission/EX bypass/FIFO change. One physical run per candidate at80MHz. Pair observations overlap unless explicitly disjoint; opportunities are not saved cycles.'))
 copy(accepted,DEST/'accepted_baseline_snapshot.json');copy(ROOT/'simulation/cleanup_dual_mul_tail_result.json',DEST/'cleanup.json');copy(ROOT/'docs/dual_mul_tail.md',DEST/'report.md')
 for n in ('generate_dual_mul_tail.py','generate_dual_pair_probe.py','run_dual_mul_tail.py','run_dual_mul_tail_v2.py','run_dual_pair_detail.py','check_dual_mul_tail_unit.py','check_dual_mul_tail_preflight.py','report_dual_mul_tail_paths.py','verify_dual_mul_tail.py','cleanup_dual_mul_tail.ps1','write_dual_mul_tail_report.py',Path(__file__).name):copy(ROOT/'tools'/n,DEST/'tools'/n)
 save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
 for n,h in read(DEST/'manifest.json').items():assert sha(DEST/n)==h,n
 print('FROZEN',preferred,len(read(DEST/'manifest.json')),'files; accepted baseline unchanged')
if __name__=='__main__':main()
