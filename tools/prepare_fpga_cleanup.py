"""Prepare the already authorized file list; preserve current evidence hashes."""
from pathlib import Path
import hashlib,json,os,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'new_core/docs/fpga_cleanup_audit_20261022'
OUT=ROOT/'new_core/docs/fpga_cleanup_execution_20261022'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def norm(p):return os.path.normcase(os.path.abspath(p))
def main():
 OUT.mkdir(exist_ok=True);assert not (OUT/'execution.json').exists(),'Cleanup already recorded'
 planfile=AUDIT/'candidate_files.json';plan=read(planfile);assert norm(plan['root'])==norm(ROOT)
 assert len(plan['candidates'])==plan['files']==4059 and sum(z['bytes'] for z in plan['candidates'])==plan['total_bytes']==5581600191
 protected=set();manifests=[];json_count=0;manifest_targets=set();tracked=[]
 def protect_ref(name,p,base):
  q=Path(name)
  choices=[q] if q.is_absolute() else [base/q,p.parent/q,ROOT/q]
  for q in choices:
   key=norm(q)
   if key.startswith(norm(ROOT)+os.sep) and q.is_file():protected.add(key)
 def walk(x,p,base):
  if not isinstance(x,dict):return
  if isinstance(x.get('sha256'),str) and re.fullmatch('[a-fA-F0-9]{64}',x['sha256']) and isinstance(x.get('path'),str):protect_ref(x['path'],p,base)
  for k,v in x.items():
   if isinstance(v,dict):
    if k.endswith('sha256'):
     for n,h in v.items():
      if isinstance(h,str) and re.fullmatch('[a-fA-F0-9]{64}',h):protect_ref(n,p,base)
    walk(v,p,base)
 for folder,children,names in os.walk(ROOT,followlinks=False):
  here=Path(folder);children[:]=[n for n in children if n!='.git' and not (here/n).is_symlink() and not (here/n).stat().st_file_attributes&0x400]
  for name in names:
   if not name.endswith('.json'):continue
   p=here/name
   if p.stat().st_size>16000000:continue
   try:x=read(p)
   except (ValueError,UnicodeError):continue
   if not isinstance(x,dict):continue
   json_count+=1;rel=p.relative_to(ROOT);base=ROOT/rel.parts[0]
   if name=='manifest.json' and x and all(isinstance(h,str) and re.fullmatch('[a-fA-F0-9]{64}',h) for h in x.values()):
    manifests.append(p);protected.add(norm(p));manifest_targets.add(p)
    for n in x:
     q=p.parent/n;protected.add(norm(q))
     if q.is_file():manifest_targets.add(q)
   walk(x,p,base)
 for project in ('CoreMark_PGL50H','CoreMark_PGL50H-2','new_core'):
  p=ROOT/project
  if not (p/'.git').exists():continue
  x=subprocess.run(['git','-C',str(p),'ls-files','-z'],capture_output=True,timeout=60);assert x.returncode==0
  for name in x.stdout.split(b'\0'):
   if name:protected.add(norm(p/os.fsdecode(name)));tracked.append(str(p/os.fsdecode(name)))
 approved=[];skipped=[];seen=set();groups=read(AUDIT/'inventory.json')['cache_groups'];objroots={str(Path(z['path'])) for z in groups if z['category']=='verilator_build_cache'}
 for z in plan['candidates']:
  rel=Path(z['path']);p=ROOT/rel;key=norm(p);reason=None
  assert not rel.is_absolute() and key.startswith(norm(ROOT)+os.sep) and key not in seen;seen.add(key)
  if key in protected or 'docs' in rel.parts or '.git' in rel.parts:reason='Now protected/tracked/referenced'
  elif not p.is_file():reason='Already absent'
  else:
   st=p.stat(follow_symlinks=False)
   if st.st_size!=z['bytes'] or st.st_mtime_ns!=z['mtime_ns']:reason='Changed since audited list'
   cursor=p
   while not reason and norm(cursor).startswith(norm(ROOT)):
    if cursor.is_symlink() or cursor.stat(follow_symlinks=False).st_file_attributes&0x400:reason='Reparse point'
    if norm(cursor)==norm(ROOT):break
    cursor=cursor.parent
  if not reason:
   cat=z['category'];parts=[n.lower() for n in rel.parts]
   allowed=(cat=='verilator_build_cache' and any(str(q) in objroots for q in rel.parents)) or (cat=='python_cache' and ('__pycache__' in parts or p.suffix=='.pyc')) or (cat=='iverilog_executable' and p.suffix=='.vvp') or (cat=='pds_compile_cache' and 'compile' in parts and ('pds' in parts or (p.parent/'screen.pds').exists())) or (cat=='pds_timing_database_cache' and p.name=='rtr.db' and 'report_timing' in parts)
   assert allowed and p.suffix.lower() not in ('.v','.hex','.bin','.elf','.idf','.rtr'),z
  if reason:skipped.append(dict(**z,reason=reason));continue
  approved.append(dict(**z,absolute_path=str(p),last_write_utc_ticks=z['mtime_ns']//100+621355968000000000))
 accepted=ROOT/'new_core/docs/accepted_dual_baseline.json';a=read(accepted);assert a['variant']=='dual_boundary_storewrite'
 critical={accepted,ROOT/'new_core/docs/accepted_baseline.json',ROOT/'new_core/hardware/pds/report_timing/top.rtr'}
 for k in ('source_sha256','ip_sha256','evidence_sha256'):
  for n,h in a[k].items():p=ROOT/'new_core'/n;assert sha(p)==h,(k,n);critical.add(p)
 assert sha(ROOT/'new_core/hardware/pds/report_timing/top.rtr')==a['single_issue_sta_sha256']
 sentinel=manifest_targets|critical
 print('Verifying protected baseline and snapshotting',len(sentinel),'protected evidence files',flush=True)
 snapshot={str(p.relative_to(ROOT)):sha(p) for p in sorted(sentinel)}
 result=dict(status='PREFLIGHT_PASS',root=str(ROOT),candidate_plan_sha256=sha(planfile),scanned_json=json_count,manifests=len(manifests),tracked_files=len(tracked),approved_files=len(approved),approved_bytes=sum(z['bytes'] for z in approved),approved=approved,skipped=skipped,protected_sha256=snapshot,critical_paths=[str(p.relative_to(ROOT)) for p in sorted(critical)],scope='Previously authorized cache list only, fresh SHA-reference/Git/manifest protection and metadata/path/reparse checks. File deletion only via native PowerShell after a second preflight.')
 (OUT/'prepared.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');print('PREPARED',len(approved),'files',result['approved_bytes'],'bytes; skipped',len(skipped))
if __name__=='__main__':main()
