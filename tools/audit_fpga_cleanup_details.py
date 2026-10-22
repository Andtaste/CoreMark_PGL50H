"""Refine PDS database classification without deleting or hashing large files."""
from pathlib import Path
from collections import Counter,defaultdict
import json,os,subprocess
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'new_core/docs/fpga_cleanup_audit_20261022'
def main():
 x=json.loads((OUT/'inventory.json').read_text(encoding='utf-8'));refs=json.loads((OUT/'protected_references.json').read_text(encoding='utf-8'));protected=set(refs['sha_references']);errors=[]
 for n in refs['manifests']:
  p=ROOT/n;protected.add(n)
  for name in json.loads(p.read_text(encoding='utf-8-sig')):protected.add(str((p.parent/name).relative_to(ROOT)))
 for n in x['git_tracked_counts']:
  z=subprocess.run(['git','-C',str(ROOT/n),'ls-files','-z'],capture_output=True,timeout=60);assert z.returncode==0
  protected.update(str(Path(n)/os.fsdecode(p)) for p in z.stdout.split(b'\0') if p)
 rows=[];totals=Counter();groups=defaultdict(Counter);candidates=[];candidate_totals=Counter();cache_roots={z['path'] for z in x['cache_groups'] if z['category']=='verilator_build_cache'}
 for folder,children,names in os.walk(ROOT,followlinks=False,onerror=lambda e:errors.append(str(e))):
  here=Path(folder);children[:]=[n for n in children if n not in ('.git','docs') and not (here/n).is_symlink() and not (here/n).stat().st_file_attributes&0x400]
  for n in names:
   p=here/n;suffix=p.suffix.lower()
   rel=p.relative_to(ROOT)
   if str(rel) in protected:continue
   anchor=next((str(q) for q in [rel.parent,*rel.parent.parents] if str(q) in cache_roots),None)
   safe=None
   if anchor:safe='verilator_build_cache'
   elif '__pycache__' in rel.parts or suffix=='.pyc':safe='python_cache'
   elif suffix=='.vvp':safe='iverilog_executable'
   elif 'compile' in [q.lower() for q in rel.parts] and ('pds' in [q.lower() for q in rel.parts] or (p.parent/'screen.pds').exists()):safe='pds_compile_cache'
   elif n=='rtr.db' and 'report_timing' in rel.parts:safe='pds_timing_database_cache'
   if safe:
    st=p.stat();candidates.append(dict(path=str(rel),bytes=st.st_size,mtime_ns=st.st_mtime_ns,category=safe));candidate_totals[safe]+=st.st_size
   if suffix not in ('.db','.netlist','.snr'):continue
   if n=='rtr.db' and 'report_timing' in rel.parts:cat='pds_timing_database_cache'
   elif n=='snr.db' or suffix=='.snr':cat='pds_synthesis_checkpoint_review'
   elif suffix=='.netlist':cat='pds_netlist_checkpoint_review'
   else:cat='other_database_review'
   size=p.stat().st_size;rows.append(dict(path=str(rel),bytes=size,category=cat));totals[cat]+=size;groups[(cat,rel.parts[0])]['bytes']+=size;groups[(cat,rel.parts[0])]['files']+=1
 result=dict(status='READ_ONLY_DETAIL',categories=dict(totals),by_project=[dict(category=c,project=n,**v) for (c,n),v in groups.items()],files=sorted(rows,key=lambda z:z['bytes'],reverse=True),errors=errors,note='Excludes Git-tracked, docs, frozen manifest and SHA-input references. rtr.db is derived timing-analysis database; retain routed input .adf and textual reports. Other databases/netlists are conditional checkpoint cleanup, not automatic deletion.')
 (OUT/'database_details.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');print(json.dumps({k:result[k] for k in ('categories','by_project','errors')},indent=2,ensure_ascii=False))
 expected={k:x['categories'][k]['bytes'] for k in ('verilator_build_cache','python_cache','iverilog_executable','pds_compile_cache')};expected['pds_timing_database_cache']=totals['pds_timing_database_cache'];assert dict(candidate_totals)==expected,(dict(candidate_totals),expected)
 (OUT/'candidate_files.json').write_text(json.dumps(dict(status='REVIEW_ONLY_NOT_DELETED',root=str(ROOT),total_bytes=sum(candidate_totals.values()),files=len(candidates),categories=dict(candidate_totals),candidates=candidates,note='Exact non-overlapping file list, not recursive directory-deletion authorization. Recheck active builds, protected references and path/size/time before any future cleanup. No RTL, firmware, result JSON, textual STA or frozen archive deletion.'),indent=2,ensure_ascii=False)+'\n',encoding='utf-8');print('EXACT CANDIDATES',len(candidates),sum(candidate_totals.values()))
if __name__=='__main__':main()
