"""Freeze reproducible RTL/IP, test evidence and routed snapshots; never adopt."""
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'docs/dual_next_trials'
TRIALS=['mqual','fqual','mpre','loadsplitv2','pairmul','pairbranch','loadcapture','wordwake','loadwake','aluwake','alulanes']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--finalize',action='store_true');ap.add_argument('--snapshots-only',action='store_true');args=ap.parse_args();assert not (DEST/'manifest.json').exists();a=read(ROOT/'docs/accepted_dual_baseline.json');ah=sha(ROOT/'docs/accepted_dual_baseline.json');assert ah=='b68472e674aa2d9e656485c85a450d7cbefcd060c96c26dd0ae8f7b61ee7882a'
 if args.snapshots_only:
  for t in TRIALS:
   src=ROOT/('simulation/results/load_bp_dual_boundary_next_'+t)
   if not (src/'pds/result.json').exists():continue
   z=DEST/t/'routed_snapshot.zip';z.parent.mkdir(parents=True,exist_ok=True)
   if not z.exists():
    with zipfile.ZipFile(z,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as ar:
     for p in [src/'pds/place_route/top_pnr.adf',src/'pds/synthesize/top_syn.vm']:ar.write(p,p.relative_to(src).as_posix())
   print('SNAPSHOT',t,flush=True)
  return
 for k in ('source_sha256','ip_sha256','evidence_sha256'):
  for n,h in a[k].items():assert sha(ROOT/n)==h,(k,n)
 def verify(x,label):
  for k in ('input_sha256','actual_compile_sha256','ip_sha256'):
   for n,h in x.get(k,{}).items():
    p=ROOT/n
    if not p.exists() and n.replace('\\','/').startswith('tmp/'):p=ROOT.parent/n
    assert p.is_file() and sha(p)==h,(label,k,n)
    if not n.replace('\\','/').startswith('simulation/results/load_bp_dual_boundary_next_') and p.suffix!='.adf':copy(p,DEST/'inputs'/n)
 prepared={}
 for t in TRIALS:
  src=ROOT/('simulation/results/load_bp_dual_boundary_next_'+t);g=read(src/'generation.json');assert g['accepted_dual_sha256']==ah
  for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
  statuses={}
  for p in src.rglob('result.json'):
   if any(k in p.parts for k in ('obj','compile','rtr.db')):continue
   x=read(p);verify(x,str(p));assert x['status'] in (('PASS','TIMING_FAILED') if p.parent.name=='pds' else ('PASS',)),p
   statuses[str(p.parent.relative_to(src))]=dict(status=x['status'],tests=len(x.get('tests',[])))
  for sub,count in [('checks',63),('pair_checks',6),('cancel_checks',4),('audit_checks',4),('protocol',8),('mul_protocol',4),('posted_soc_final',6),('uart80',1),('timeline_checks',4),('next_suite',10)]:assert statuses[sub]['tests']==count,(t,sub,statuses.get(sub))
  if t in ('mqual','fqual','loadcapture'):assert statuses['operand_checks']['tests']==3
  if t in ('loadwake','wordwake','aluwake','alulanes'):assert statuses['operands_checks']['tests']==3
  if t in ('mpre','loadsplitv2','pairmul','pairbranch'):assert statuses['next_directed']['tests']==6
  if t in ('pairmul','loadsplitv2'):assert statuses['next_memory_checks']['tests']==2
  if t in ('pairmul','loadsplitv2','loadcapture','loadwake','wordwake'):assert statuses['posted_module']['tests']==8
  pd=read(src/'pds/result.json');assert pd['pds_exit_code']==0 and sha(src/'pds/run.tcl')==pd['tcl_sha256']
  snaps=[src/'pds/place_route/top_pnr.adf',src/'pds/synthesize/top_syn.vm'];z=DEST/t/'routed_snapshot.zip';z.parent.mkdir(parents=True,exist_ok=True)
  if not z.exists():
   with zipfile.ZipFile(z,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as ar:
    for p in snaps:ar.write(p,p.relative_to(src).as_posix())
  with zipfile.ZipFile(z) as ar:
   for p in snaps:assert hashlib.sha256(ar.read(p.relative_to(src).as_posix())).hexdigest()==sha(p)
  prepared[t]=dict(checks=statuses,snapshot_sha256={str(p.relative_to(src)):sha(p) for p in snaps})
  for p in src.rglob('*'):
   if not p.is_file():continue
   rel=p.relative_to(src)
   if any(k in rel.parts for k in ('obj','compile','rtr.db')) or p.suffix in ('.vvp','.o','.exe','.pyc','.elf','.bin'):continue
   if rel.parts[0]=='pds' and rel.as_posix() not in ('pds/result.json','pds/run.tcl','pds/build.log','pds/report_timing/top.rtr','pds/device_map/top.dmr','pds/place_route/top.prr','pds/synthesize/apm_drm_lutram_utilization.log'):continue
   if rel.parts[0]=='next_paths' and len(rel.parts)>2:continue
   copy(p,DEST/t/rel)
 # Preserve observation and rejected first split independently, without treating failure as a candidate.
 for name in ('probe','loadsplit'):
  src=ROOT/('simulation/results/load_bp_dual_boundary_next_'+name)
  for p in src.rglob('*'):
   if p.is_file() and 'obj' not in p.parts and p.suffix in ('.v','.json','.log','.txt','.hex','.S'):copy(p,DEST/('observation' if name=='probe' else 'failures/loadsplit/full_record')/p.relative_to(src))
 for dirname in ('dual_next_reproduction','dual_next_reproduction_alulanes'):
  verify(read(ROOT/'simulation/results'/dirname/'result.json'),dirname)
  for p in (ROOT/'simulation/results'/dirname).rglob('*'):
   if p.is_file():copy(p,DEST/'reproduction'/dirname/p.relative_to(ROOT/'simulation/results'/dirname))
 for tool in (ROOT/'tools').glob('*next*'):
  if tool.is_file():copy(tool,DEST/'tools'/tool.name)
 copy(ROOT/'tools/run_dual_mul_tail_v2.py',DEST/'tools/run_dual_mul_tail_v2.py')
 selected=ROOT/'simulation/results/load_bp_dual_boundary_storewrite/next_paths'
 if (selected/'result.json').exists():
  verify(read(selected/'result.json'),'baseline read-only queries')
  for p in selected.iterdir():
   if p.is_file():copy(p,DEST/'baseline_paths'/p.name)
 prior={}
 for name in ('dual_forward_control','dual_timing_simplify','dual_mul_tail','dual_store_simple_adoption'):
  folder=ROOT/'docs'/name;m=read(folder/'manifest.json')
  for n,h in m.items():assert sha(folder/n)==h,(name,n)
  prior[name]=len(m)
 copy(ROOT/'docs/accepted_dual_baseline.json',DEST/'accepted_baseline_snapshot.json');copy(ROOT/'docs/dual_next_trials.md',DEST/'report.md')
 v=ROOT/'simulation/results/dual_next_reproduction/result.json';assert read(v)['status']=='PASS';verify(read(v),'exact regeneration')
 save(DEST/'archive_verification.json',dict(status='PASS',accepted_descriptor_sha256=ah,candidates=prepared,prior_frozen_files_verified=prior))
 if args.finalize:
  cleanup=ROOT/'simulation/cleanup_dual_next_trials_result.json';assert read(cleanup)['status']=='PASS';copy(cleanup,DEST/'cleanup.json')
  save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
  for n,h in read(DEST/'manifest.json').items():assert sha(DEST/n)==h,n
  print('FROZEN',len(read(DEST/'manifest.json')),'files; accepted descriptor unchanged',ah)
 else:print('PREPARED verified snapshots and source/test evidence; caches may now be removed')
if __name__=='__main__':main()
