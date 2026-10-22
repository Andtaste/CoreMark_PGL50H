"""Freeze equivalent timing trials without changing the accepted CPU."""
from pathlib import Path
import hashlib,json,re,shutil,zipfile
from parse_dual_joint_timing import paths
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'docs/dual_timing_simplify'
NAMES=['dual_boundary_'+s for s in ('bankreq','banklocal','wbflags')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
 assert not (DEST/'manifest.json').exists();DEST.mkdir(exist_ok=True)
 accepted=ROOT/'docs/accepted_dual_baseline.json';ah=sha(accepted);a=read(accepted)
 assert a['variant']=='dual_boundary_storewrite'
 for k in ('source_sha256','ip_sha256','evidence_sha256'):
  for n,h in a[k].items():assert sha(ROOT/n)==h,(k,n)
 for k,n in (('single_issue_reference_sha256','docs/accepted_baseline.json'),('single_issue_sta_sha256','hardware/pds/report_timing/top.rtr')):assert sha(ROOT/n)==a[k]
 prior={}
 for name in ('dual_mul_tail','dual_store_simple','dual_store_simple_adoption','dual_mem_ipc','dual_timing80'):
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
 for name,gen in zip(NAMES,('generate_dual_bank_timing.py','generate_dual_bank_local.py','generate_dual_wb_flags.py')):
  src=ROOT/('simulation/results/load_bp_'+name);g=read(src/'generation.json');verify(g,name)
  assert g['accepted_dual_sha256']==ah and sha(ROOT/'tools'/gen)==g['generator_sha256']
  for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
  statuses={}
  for p in src.rglob('result.json'):
   if 'obj' in p.parts:continue
   x=read(p);verify(x,str(p));assert x['status']==('TIMING_FAILED' if p.parent.name=='pds' else 'PASS'),p
   statuses[str(p.parent.relative_to(src))]=dict(status=x['status'],tests=len(x.get('tests',[])))
  counts=dict(checks=63,pair_checks=6,cancel_checks=4,audit_checks=4,timeline_checks=4,protocol=8,mul_protocol=4,memory_checks=4,address_contract=10,posted_module=8,posted_soc_final=6,uart80=1)
  counts.update(dict(wb_flag_proof=1) if name.endswith('wbflags') else dict(bank_memory_proof=4,bank_bus_proof=2))
  for sub,count in counts.items():assert statuses[sub]['tests']==count,(name,sub)
  assert statuses['bank_paths']['status']=='PASS'
  sim=read(src/'performance/result.json');pd=read(src/'pds/result.json')
  assert pd['pds_exit_code']==0 and sha(src/'pds/run.tcl')==pd['tcl_sha256']
  assert re.search(r'12\.500\s+\{0 6\.25\}',(src/'pds/report_timing/top.rtr').read_text(errors='replace'))
  assert int(sim['metrics']['Stats window cycles'])==2704650 and int(sim['metrics']['Retired instructions'])==2808261
  row=dict(checks=statuses,metrics=sim['metrics'],ipc=2808261/2704650,timing_status=pd['status'],estimated_fmax_mhz=pd['estimated_fmax_mhz'],resources=pd['resources'],corners=pd['corners'],global_paths=paths(src/'pds/report_timing/top.rtr'),selected_paths=read(src/'bank_paths/result.json')['paths'])
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
   if rel.parts[0]=='bank_paths' and len(rel.parts)>2:continue
   copy(p,DEST/name/rel)
 for n in ('dual_bank_timing_verify','dual_wb_flags_verify'):
  d=ROOT/'simulation/results'/n;x=read(d/'result.json');verify(x,n);assert x['status']=='PASS'
  for p in d.rglob('*'):
   if p.is_file():copy(p,DEST/'verification'/n/p.relative_to(d))
 save(DEST/'comparison.json',dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',preferred_candidate=None,accepted_descriptor_sha256=ah,accepted=a,candidates=rows,prior_archive_verified_files=prior,note='All three candidates fail80MHz setup; all hold corners pass. Same IPC/cycles, one physical run per candidate, no constraint relaxation or added pipeline cycle.'))
 copy(accepted,DEST/'accepted_baseline_snapshot.json');copy(ROOT/'simulation/cleanup_dual_timing_simplify_result.json',DEST/'cleanup.json');copy(ROOT/'docs/dual_timing_simplify.md',DEST/'report.md')
 names=['check_dual_bank_bus.py','check_dual_bank_memory.py','check_dual_bank_soc.py','check_dual_wb_flags.py','cleanup_dual_timing_simplify.ps1','generate_dual_bank_local.py','generate_dual_bank_timing.py','generate_dual_wb_flags.py','report_dual_bank_paths.py','verify_dual_bank_timing.py','verify_dual_wb_flags.py',Path(__file__).name]
 for n in names:copy(ROOT/'tools'/n,DEST/'tools'/n)
 save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
 for n,h in read(DEST/'manifest.json').items():assert sha(DEST/n)==h,n
 assert sha(accepted)==ah
 print('FROZEN',len(read(DEST/'manifest.json')),'files; no candidate recommended; baseline unchanged')
if __name__=='__main__':main()
