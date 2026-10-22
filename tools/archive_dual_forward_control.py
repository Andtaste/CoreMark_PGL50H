"""Freeze forwarding/control mux experiments; preserve accepted source/evidence."""
from pathlib import Path
import hashlib,json,re,shutil,zipfile
from parse_dual_joint_timing import paths
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'docs/dual_forward_control'
NAMES=['dual_boundary_'+s for s in ('headmux','pcselect','headlocal')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
 assert not (DEST/'manifest.json').exists();DEST.mkdir(exist_ok=True)
 accepted=ROOT/'docs/accepted_dual_baseline.json';ah=sha(accepted);a=read(accepted);assert a['variant']=='dual_boundary_storewrite'
 for k in ('source_sha256','ip_sha256','evidence_sha256'):
  for n,h in a[k].items():assert sha(ROOT/n)==h,(k,n)
 for k,n in (('single_issue_reference_sha256','docs/accepted_baseline.json'),('single_issue_sta_sha256','hardware/pds/report_timing/top.rtr')):assert sha(ROOT/n)==a[k]
 prior={}
 for name in ('dual_timing_simplify','dual_mul_tail','dual_store_simple','dual_store_simple_adoption','dual_mem_ipc','dual_timing80'):
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
 for name,gen,proof,count in zip(NAMES,('generate_dual_forward_control.py','generate_dual_pc_select.py','generate_dual_head_local.py'),('forward_equivalence','execute_equivalence','forward_equivalence'),(1,2,1)):
  src=ROOT/('simulation/results/load_bp_'+name);g=read(src/'generation.json');verify(g,name)
  assert g['accepted_dual_sha256']==ah and sha(ROOT/'tools'/gen)==g['generator_sha256']
  for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
  statuses={}
  for p in src.rglob('result.json'):
   if 'obj' in p.parts:continue
   x=read(p);verify(x,str(p));assert x['status'] in (('PASS','TIMING_FAILED') if p.parent.name=='pds' else ('PASS',)),p
   statuses[str(p.parent.relative_to(src))]=dict(status=x['status'],tests=len(x.get('tests',[])))
  for sub,num in (('checks',63),('pair_checks',6),('cancel_checks',4),('audit_checks',4),('protocol',8),('mul_protocol',4),('posted_soc_final',6),('uart80',1),('timeline_checks',4),(proof,count)):
   assert statuses[sub]['tests']==num,(name,sub)
  assert statuses['integration_run']['status']=='PASS'
  sim=read(src/'performance/result.json');pd=read(src/'pds/result.json');assert pd['pds_exit_code']==0 and sha(src/'pds/run.tcl')==pd['tcl_sha256']
  assert re.search(r'12\.500\s+\{0 6\.25\}',(src/'pds/report_timing/top.rtr').read_text(errors='replace'))
  assert int(sim['metrics']['Stats window cycles'])==2704650 and int(sim['metrics']['Retired instructions'])==2808261
  row=dict(checks=statuses,metrics=sim['metrics'],ipc=2808261/2704650,timing_status=pd['status'],estimated_fmax_mhz=pd['estimated_fmax_mhz'],resources=pd['resources'],corners=pd['corners'],global_paths=paths(src/'pds/report_timing/top.rtr'))
  snaps=[src/'pds/place_route/top_pnr.adf',src/'pds/synthesize/top_syn.vm'];z=DEST/name/'routed_snapshot.zip';z.parent.mkdir(parents=True,exist_ok=True)
  with zipfile.ZipFile(z,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as ar:
   for p in snaps:ar.write(p,p.relative_to(src).as_posix())
  with zipfile.ZipFile(z) as ar:
   for p in snaps:assert hashlib.sha256(ar.read(p.relative_to(src).as_posix())).hexdigest()==sha(p)
  row['routed_snapshot_sha256']={str(p.relative_to(src)):sha(p) for p in snaps};rows[name]=row
  for p in src.rglob('*'):
   if not p.is_file():continue
   rel=p.relative_to(src)
   if 'obj' in rel.parts or p.suffix in ('.vvp','.o','.exe','.pyc','.elf','.bin'):continue
   if rel.parts[0]=='pds' and rel.as_posix() not in ('pds/result.json','pds/run.tcl','pds/build.log','pds/report_timing/top.rtr','pds/device_map/top.dmr','pds/place_route/top.prr','pds/synthesize/apm_drm_lutram_utilization.log'):continue
   copy(p,DEST/name/rel)
 for dirname in ('dual_forward_control_verify','dual_head_local_verify'):
  d=ROOT/'simulation/results'/dirname;x=read(d/'result.json');verify(x,'exact_reproduction');assert x['status']=='PASS'
  for p in d.rglob('*'):
   if p.is_file():copy(p,DEST/'verification'/dirname/p.relative_to(d))
 for name in ['dual_boundary_storewrite',*NAMES]:
  d=ROOT/'simulation/results/dual_forward_control_paths'/name;x=read(d/'result.json');verify(x,name+' selected paths');assert x['status']=='PASS'
  for n,h in x['report_sha256'].items():assert sha(d/n)==h
  for p in d.iterdir():
   if p.is_file():copy(p,DEST/'selected_paths'/name/p.name)
  if name in rows:rows[name]['selected_paths']=x['paths']
 eligible=[n for n in NAMES if rows[n]['timing_status']=='PASS' and rows[n]['estimated_fmax_mhz']>a['estimated_fmax_mhz']]
 preferred=max(eligible,key=lambda n:rows[n]['estimated_fmax_mhz'],default=None)
 save(DEST/'comparison.json',dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',preferred_candidate=preferred,accepted_descriptor_sha256=ah,accepted=a,candidates=rows,prior_archive_verified_files=prior,note='Previous bankreq/banklocal/wbflags explicitly rejected by user. All three current candidates independently start at accepted storewrite; no combined variant. Same IPC/cycles; one physical run per candidate at80MHz; no new pipeline stage or relaxed timing constraints.'))
 copy(accepted,DEST/'accepted_baseline_snapshot.json');copy(ROOT/'simulation/cleanup_dual_forward_control_result.json',DEST/'cleanup.json');copy(ROOT/'simulation/cleanup_dual_head_local_result.json',DEST/'cleanup_head_local.json');copy(ROOT/'docs/dual_forward_control.md',DEST/'report.md')
 for n in ('generate_dual_forward_control.py','check_dual_forward_control.py','generate_dual_pc_select.py','check_dual_pc_select.py','generate_dual_head_local.py','verify_dual_head_local.py','report_dual_head_local_paths.py','cleanup_dual_head_local.ps1','run_dual_forward_checks.py','report_dual_forward_paths.py','verify_dual_forward_control.py','cleanup_dual_forward_control.ps1','write_dual_forward_report.py',Path(__file__).name):copy(ROOT/'tools'/n,DEST/'tools'/n)
 save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
 for n,h in read(DEST/'manifest.json').items():assert sha(DEST/n)==h,n
 assert sha(accepted)==ah;print('FROZEN',len(read(DEST/'manifest.json')),'files; recommended',preferred,'; accepted baseline unchanged')
if __name__=='__main__':main()
