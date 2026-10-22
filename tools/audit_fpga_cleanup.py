"""Read-only FPGA workspace cleanup inventory; never deletes project files."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,os,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'new_core/docs/fpga_cleanup_audit_20261022'
def main():
 files=[];dirs=Counter();counts=Counter();skipped=[];errors=[];cache_roots=set()
 for folder,children,names in os.walk(ROOT,followlinks=False):
  here=Path(folder)
  for n in list(children):
   p=here/n
   try:
    if p.is_symlink() or p.stat().st_file_attributes & 0x400:children.remove(n);skipped.append(str(p.relative_to(ROOT)))
   except OSError as e:children.remove(n);errors.append(str(e))
  if (here.name=='obj' or here.name=='obj_dir' or here.name.endswith('_obj') or here.name.startswith('obj_')) and any(n.startswith('V') and n.endswith(('.cpp','.mk')) for n in names):cache_roots.add(str(here.relative_to(ROOT)))
  for n in names:
   p=here/n
   try:
    st=p.stat(follow_symlinks=False)
    if p.is_symlink() or st.st_file_attributes & 0x400:skipped.append(str(p.relative_to(ROOT)));continue
    rel=p.relative_to(ROOT);files.append((rel,st.st_size))
    for d in [rel.parent,*rel.parent.parents]:
     dirs[str(d)]+=st.st_size;counts[str(d)]+=1
   except OSError as e:errors.append(str(e))
 tracked=set();repos={}
 for n in ('CoreMark_PGL50H','CoreMark_PGL50H-2','new_core'):
  p=ROOT/n
  if not (p/'.git').exists():continue
  x=subprocess.run(['git','-C',str(p),'ls-files','-z'],capture_output=True,timeout=60)
  if x.returncode==0:
   items=[str(Path(n)/os.fsdecode(z)) for z in x.stdout.split(b'\0') if z];tracked.update(items);repos[n]=len(items)
 frozen=set();references=defaultdict(list);manifests=[];json_errors=[]
 for rel,size in files:
  if rel.suffix.lower()!='.json' or size>16000000:continue
  p=ROOT/rel
  try:x=json.loads(p.read_text(encoding='utf-8-sig'))
  except (ValueError,UnicodeError,OSError):continue
  if not isinstance(x,dict):continue
  if p.name=='manifest.json' and x and all(isinstance(h,str) and re.fullmatch('[0-9a-fA-F]{64}',h) for h in x.values()):
   manifests.append(str(rel));frozen.add(str(rel))
   for n in x:frozen.add(str((p.parent/n).relative_to(ROOT)))
  base=ROOT/'new_core' if rel.parts[0]=='new_core' else ROOT/rel.parts[0]
  def walk(obj):
   if not isinstance(obj,dict):return
   for k,v in obj.items():
    if k in ('input_sha256','actual_compile_sha256','ip_sha256','source_sha256','evidence_sha256') and isinstance(v,dict):
     for name,h in v.items():
      if not isinstance(h,str) or not re.fullmatch('[0-9a-fA-F]{64}',h):continue
      q=Path(name)
      if not q.is_absolute():
       q=base/q
       if not q.exists() and name.replace('\\','/').startswith('tmp/'):q=ROOT/name
      try:
       key=str(q.relative_to(ROOT))
       if len(references[key])<4:references[key].append(str(rel))
      except ValueError:pass
    elif isinstance(v,dict):walk(v)
  walk(x)
 totals=Counter();cat_files=Counter();by_project=defaultdict(Counter);groups=defaultdict(lambda:Counter(bytes=0,files=0));largest=defaultdict(list);frozen_total=0;ref_total=0
 for rel,size in files:
  s=str(rel);parts=rel.parts;low=[p.lower() for p in parts];suffix=rel.suffix.lower();protected=s in tracked or s in frozen or s in references or '.git' in parts or 'docs' in low
  if s in frozen:frozen_total+=size
  if s in references:ref_total+=size
  anchor=next((str(p) for p in [rel.parent,*rel.parent.parents] if str(p) in cache_roots),None)
  if protected:cat='protected_source_or_evidence'
  elif anchor:cat='verilator_build_cache'
  elif '__pycache__' in parts or suffix=='.pyc':cat='python_cache'
  elif suffix=='.vvp':cat='iverilog_executable'
  elif suffix in ('.vcd','.fst','.wlf'):cat='waveform_review'
  elif 'compile' in low and ('pds' in low or (ROOT/rel.parent/'screen.pds').exists()):cat='pds_compile_cache'
  elif suffix in ('.o','.d') and ('sw' in low or 'build' in low):cat='software_object_cache'
  elif suffix=='.trace':cat='simulation_trace_review'
  elif suffix=='.log':cat='log_review'
  elif suffix in ('.adf','.vm','.edf','.edif'):cat='pds_checkpoint_review'
  elif suffix in ('.zip','.7z','.gz','.tar'):cat='archive_keep'
  else:cat='other_keep_or_review'
  totals[cat]+=size;cat_files[cat]+=1;by_project[parts[0]][cat]+=size;largest[cat].append((size,s))
  if cat in ('verilator_build_cache','pds_compile_cache','python_cache'):
   if cat=='verilator_build_cache':target=anchor
   elif cat=='python_cache':target=str(Path(*parts[:parts.index('__pycache__')+1])) if '__pycache__' in parts else s
   else:target=str(Path(*parts[:low.index('compile')+1]))
   groups[(cat,target)]['bytes']+=size;groups[(cat,target)]['files']+=1
 for cat in largest:largest[cat]=[dict(bytes=z,path=n) for z,n in sorted(largest[cat],reverse=True)[:30]]
 OUT.mkdir(parents=True,exist_ok=True)
 result=dict(status='READ_ONLY_INVENTORY',date='2026-10-22',root=str(ROOT),total_bytes=dirs['.'],total_files=len(files),categories={k:dict(bytes=v,files=cat_files[k]) for k,v in totals.items()},top_level={n:dict(bytes=z,files=counts[n]) for n,z in dirs.items() if len(Path(n).parts)==1 and n!='.'},largest_dirs=[dict(path=n,bytes=z,files=counts[n]) for n,z in sorted(dirs.items(),key=lambda kv:kv[1],reverse=True) if n!='.' and len(Path(n).parts)<=4][:100],cache_groups=[dict(category=c,path=n,**z) for (c,n),z in sorted(groups.items(),key=lambda kv:kv[1]['bytes'],reverse=True)],largest_files=largest,by_project={k:dict(v) for k,v in by_project.items()},git_tracked_counts=repos,manifest_count=len(manifests),frozen_existing_bytes=frozen_total,referenced_existing_bytes=ref_total,skipped_reparse=skipped,errors=errors,note='Candidate categories exclude tracked files, manifest-protected files, docs and SHA-input references. Directory totals may include retained files; group bytes count candidates only. Sizes are logical bytes, not guaranteed physical disk reclamation. No deletion or archive transformation performed.')
 (OUT/'inventory.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 (OUT/'protected_references.json').write_text(json.dumps(dict(manifests=manifests,sha_references=dict(references)),indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print(json.dumps({k:result[k] for k in ('total_bytes','total_files','categories','top_level','manifest_count','git_tracked_counts','errors')},indent=2,ensure_ascii=False))
 print('TOP_CACHE_GROUPS',json.dumps(result['cache_groups'][:12],ensure_ascii=False))
 print('TOP_REVIEW_FILES',json.dumps({k:v[:5] for k,v in largest.items() if k in ('simulation_trace_review','pds_checkpoint_review','log_review','waveform_review')},ensure_ascii=False))
if __name__=='__main__':main()
