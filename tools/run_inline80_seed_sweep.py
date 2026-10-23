"""Bounded six-run actual83MHz sweep, preserving accepted hardware and evidence."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'simulation/results/continuous_clock83_inline80_sweep_20261022'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cleanup():
 subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'tools/clean_completed_clock_trials.ps1')],cwd=ROOT,check=True)
def main():
 meta=json.loads((BASE/'prepared.json').read_text())
 for n,h in meta['input_sha256'].items():assert sha(BASE/n)==h,n
 rows=[]
 for strategy in ('default','fanout64'):
  for ps,rs in ((3,1),(0,0),(7,2)):
   dest=BASE.parent/f'continuous_clock83_inline80_{strategy}_p{ps}r{rs}_20261022'
   if dest.exists():
    old=json.loads((dest/'prepared.json').read_text())
    for n,h in old['input_sha256'].items():assert sha(dest/n)==h,n
    result=json.loads((dest/'evaluation.json').read_text())
    assert result['status'] in ('PASS','FAIL') and result['sta_sha256']==sha(dest/'report_timing/top.rtr')
    rows.append(result);cleanup();continue
   dest.mkdir()
   for folder in ('source','ipcore','constraints','memory'):shutil.copytree(BASE/folder,dest/folder)
   for p in (dest/'ipcore').rglob('*'):
    if p.is_file() and p.suffix in ('.v','.idf','.vhdl'):p.write_bytes(p.read_bytes().replace(BASE.as_posix().encode(),dest.as_posix().encode()))
   for folder in ('source','ipcore','constraints','memory'):
    for p in (dest/folder).rglob('*'):
     if p.is_file():assert p.read_bytes().replace(dest.as_posix().encode(),BASE.as_posix().encode())==(BASE/p.relative_to(dest)).read_bytes()
   for n in ('parent_baseline.json','parent_compiler_profile.json'):shutil.copyfile(BASE/n,dest/n)
   s=(BASE/'new_core.pds').read_text()
   for key,v in (('gplace_seed',ps),('groute_seed',rs)):
    s,count=re.subn(r'\(_option '+key+r' \(_integer \d+\)\)',f'(_option {key} (_integer {v}))',s);assert count==1
   changed={}
   if strategy=='fanout64':
    needle='(_option selected_syn_tool_opt (_integer 2))';assert s.count(needle)==1
    s=s.replace(needle,needle+'\n            (_option fanout_guide (_integer 64))');changed={'fanout_guide':64}
   (dest/'new_core.pds').write_text(s)
   row=dict(meta,strategy=strategy,changed_option=changed,place_seed=ps,route_seed=rs)
   row['input_sha256']={str(p.relative_to(dest)):sha(p) for f in ('source','ipcore','constraints','memory') for p in (dest/f).rglob('*') if p.is_file()}
   (dest/'prepared.json').write_text(json.dumps(row,indent=2)+'\n')
   print('START',strategy,ps,rs,flush=True)
   with (dest/'native_build.log').open('wb') as f:
    subprocess.run(['E:/pango/PDS_2022.2-SP1-Lite/bin/pds_shell.exe','-project','new_core.pds','-run','report_timing'],cwd=dest,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=3600)
   log=(dest/'native_build.log').read_text(errors='replace')
   assert 'Process "Report Timing" done.' in log and not re.search(r'^E:',log,re.M),dest
   subprocess.run([sys.executable,str(ROOT/'tools/report_continuous_clocks.py')],cwd=ROOT,stdout=subprocess.DEVNULL,check=True)
   result=json.loads((dest/'evaluation.json').read_text());rows.append(result)
   (BASE/'sweep_results.json').write_text(json.dumps(rows,indent=2)+'\n')
   print('RESULT',strategy,ps,rs,result['status'],result['estimated_fmax_mhz'],flush=True)
   cleanup()
 print('SWEEP_COMPLETE',len(rows),flush=True)
if __name__=='__main__':main()
