"""Freeze isolated store-ack trials, their failures, and exact inputs."""
from pathlib import Path
import hashlib,json,re,shutil,zipfile
from parse_dual_joint_timing import paths
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'docs/dual_mem_ipc'
NAMES=['dual_boundary_'+n for n in ('memprobe','storeack','storemmio','storeprefix')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def main():
 assert not (DEST/'manifest.json').exists();DEST.mkdir(exist_ok=True);accepted=ROOT/'docs/accepted_dual_baseline.json';a=read(accepted);assert a['variant']=='dual_boundary_slots'
 for k in ('source_sha256','ip_sha256','evidence_sha256'):
  for n,h in a[k].items():assert sha(ROOT/n)==h,(k,n)
 for k,n in (('single_issue_reference_sha256','docs/accepted_baseline.json'),('single_issue_sta_sha256','hardware/pds/report_timing/top.rtr')):assert sha(ROOT/n)==a[k]
 old=ROOT/'docs/dual_timing80';m=read(old/'manifest.json')
 for n,h in m.items():assert sha(old/n)==h,('prior archive',n)
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
  genname={'dual_boundary_memprobe':'generate_dual_mem_ipc.py','dual_boundary_storeack':'generate_dual_store_ack.py','dual_boundary_storemmio':'generate_dual_store_ack_mmio.py','dual_boundary_storeprefix':'generate_dual_store_prefix.py'}[name]
  gen=ROOT/'tools'/genname;assert sha(gen)==g['generator_sha256'];copy(gen,DEST/'tools'/genname)
  for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
  statuses={}
  for p in src.rglob('result.json'):
   if 'obj' in p.parts:continue
   x=read(p);verify(x,str(p))
   if p.parent.name!='pds':assert x['status']=='PASS',p
   statuses[str(p.parent.relative_to(src))]=dict(status=x['status'],tests=len(x.get('tests',[])))
  sim=read(src/'performance/result.json');cycles=int(sim['metrics']['Stats window cycles']);ret=int(sim['metrics']['Retired instructions'])
  row=dict(cycles=cycles,retired=ret,ipc=ret/cycles,mem_ipc=sim['mem_ipc'],load_queue=sim['load_queue'],dual=sim['dual'],checks=statuses)
  if name.endswith('storeprefix'):
   for sub,count in (('checks',63),('pair_checks',6),('cancel_checks',4),('audit_checks',4),('timeline_checks',4),('memory_checks',4),('address_contract',10),('protocol',8),('mul_protocol',4),('posted_module',8),('posted_soc_final',6),('range_proof',1)):assert statuses[sub]['tests']==count,(sub,statuses.get(sub))
   assert statuses['uart80']['status']=='PASS'
  if name.endswith('memprobe'):assert cycles==2807614 and ret==2808261
  else:
   assert cycles==2704650 and ret==2808261
   pd=read(src/'pds/result.json');assert pd['pds_exit_code']==0 and sha(src/'pds/run.tcl')==pd['tcl_sha256']
   assert re.search(r'12\.500\s+\{0 6\.25\}',(src/'pds/report_timing/top.rtr').read_text(errors='replace'))
   row.update(timing_status=pd['status'],estimated_fmax_mhz=pd['estimated_fmax_mhz'],resources=pd['resources'],corners=pd['corners'],global_paths=paths(src/'pds/report_timing/top.rtr'),selected_paths=read(src/'mem_paths/result.json')['paths'])
   snaps=[src/'pds/place_route/top_pnr.adf',src/'pds/synthesize/top_syn.vm']
   # Preserve the actual route, avoiding duplicate STA work databases.
   snaps=[p for p in snaps if p.exists()];assert snaps and snaps[0].suffix=='.adf'
   z=DEST/name/'routed_snapshot.zip';z.parent.mkdir(parents=True,exist_ok=True)
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
   if rel.parts[0]=='mem_paths' and len(rel.parts)>2:continue
   copy(p,DEST/name/rel)
 for dirname in ('dual_mem_ipc_verify','dual_store_prefix_verify'):
  src=ROOT/'simulation/results'/dirname
  for p in src.rglob('*.json'):
   x=read(p)
   if p.name!='generation.json':verify(x,str(p));assert x['status']=='PASS'
  for p in src.rglob('*'):
   if p.is_file():copy(p,DEST/dirname/p.relative_to(src))
 copy(accepted,DEST/'accepted_baseline_snapshot.json');copy(ROOT/'simulation/cleanup_dual_mem_ipc_result.json',DEST/'cleanup.json')
 comparison=dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',accepted_descriptor_sha256=sha(accepted),accepted=a,candidates=rows,prior_archive_verified_files=len(m),note='Each physical trial used one PDS run at 80MHz; no timing exceptions or seed sweep. Generic core posted stores default OFF; fixed local SoC enables no-late-error acknowledgement. Fixed software prints75MHz; IPC computed independently. No board result.')
 save(DEST/'comparison.json',comparison)
 report=ROOT/'docs/dual_mem_ipc.md';assert report.exists();copy(report,DEST/'report.md');copy(Path(__file__).resolve(),DEST/'tools'/Path(__file__).name)
 for n in ('write_dual_mem_ipc_report.py','cleanup_dual_mem_ipc.ps1','verify_dual_mem_ipc.py','verify_dual_store_prefix.py'):
  copy(ROOT/'tools'/n,DEST/'tools'/n)
 save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
 for n,h in read(DEST/'manifest.json').items():assert sha(DEST/n)==h,n
 print('FROZEN',len(read(DEST/'manifest.json')),'files; accepted baseline unchanged')
if __name__=='__main__':main()
