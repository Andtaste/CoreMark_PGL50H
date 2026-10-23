"""Bounded native timing trials for the verified comparison correction."""
from pathlib import Path
import argparse,concurrent.futures,json,re,shutil,subprocess
from verify_board_pnr import inspect,sha
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'simulation/results/report_compare_fix83_20261023'
FANOUT=64
PRIORITY=False
def run(pair):
 seed,route=pair
 suffix='' if FANOUT==64 else f'_f{FANOUT}'
 if PRIORITY:suffix+='_priority'
 p=BASE.with_name(BASE.name+suffix+f'_p{seed}r{route}');p.mkdir()
 for n in ('source','ipcore','constraints','memory'):shutil.copytree(BASE/n,p/n)
 for n in ('boot_interleaved.hex','generate_bitstream.tcl'):shutil.copyfile(BASE/n,p/n)
 s=(BASE/'new_core.pds').read_text()
 s=re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',s)
 for k,v in [('gplace_seed',seed),('groute_seed',route)]:s=re.sub(r'\(_option '+k+r' \(_integer \d+\)\)',f'(_option {k} (_integer {v}))',s)
 s,count=re.subn(r'\(_option fanout_guide \(_integer \d+\)\)',f'(_option fanout_guide (_integer {FANOUT}))',s);assert count==1
 if PRIORITY:
  needle='(_option max_ctrl_chain_length (_integer 4))';assert s.count(needle)==1
  s=s.replace(needle,needle+'\n            (_option enable_route_constraint_iterate (_switch ON))\n            (_option route_constraint_iterate_times (_integer 4))\n            (_option route_constraint_slack (_real 0.05))\n            (_option route_constraint_max_timing_path (_integer 5))')
 (p/'new_core.pds').write_text(s)
 print('START',p.name,flush=True)
 with (p/'native_build.log').open('wb') as f:subprocess.run(['E:/pango/PDS_2022.2-SP1-Lite/bin/pds_shell.exe','-project','new_core.pds','-run','report_timing'],cwd=p,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=3600)
 log=(p/'native_build.log').read_text(errors='replace');assert 'Process "Report Timing" done.' in log and not re.search(r'^E:',log,re.M)
 try:r=inspect(p,83)
 except AssertionError as e:
  t=(p/'report_timing/top.rtr').read_text();m=re.search(r'(\d+\.\d+) MHz\s+(\d+\.\d+) MHz',t)
  r={'status':'FAIL','reason':str(e),'estimated_fmax_mhz':float(m[2]),'sta_sha256':sha(p/'report_timing/top.rtr')}
 r.update(place_seed=seed,route_seed=route,fanout_guide=FANOUT,project=str(p.relative_to(ROOT)))
 r['priority_routing']=PRIORITY
 (p/'physical_result.json').write_text(json.dumps(r,indent=2))
 print('DONE',p.name,r['status'],r['estimated_fmax_mhz'],flush=True)
 return r
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--base',default=str(BASE));ap.add_argument('--pairs',nargs='+',default=['0,0','3,0']);ap.add_argument('--fanout',type=int,default=64);ap.add_argument('--priority',action='store_true');a=ap.parse_args();BASE=Path(a.base).resolve();FANOUT=a.fanout;PRIORITY=a.priority
 assert BASE.is_relative_to(ROOT/'simulation/results')
 pairs=[tuple(map(int,p.split(','))) for p in a.pairs];assert all(len(p)==2 for p in pairs)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:rows=list(ex.map(run,pairs))
 suffix=f'f{FANOUT}_'+('priority_' if PRIORITY else '')+'_'.join(f'p{p}r{r}' for p,r in pairs)
 (BASE/f'seed_results_{suffix}.json').write_text(json.dumps(rows,indent=2))
