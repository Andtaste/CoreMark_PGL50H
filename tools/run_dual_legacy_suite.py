"""Complete staged checks; every subprocess writes its own immutable evidence."""
from pathlib import Path
import argparse,subprocess,sys,json
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);ap.add_argument('--exclude',default='');a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);out=src/'suite';out.mkdir(exist_ok=True)
 tasks=[]
 for phase in ('checks','validation'):
  if not (src/phase/'result.json').exists():tasks.append((phase,['tools/run_dual_legacy.py','--phase',phase]))
 for mode,sub in [('extra','dual_checks'),('pairs','pair_checks'),('operands','operands_checks'),('timeline','timeline_checks'),('audit','audit_checks')]:
  if not (src/sub/'result.json').exists():tasks.append((mode,['tools/check_dual_legacy.py','--mode',mode]))
 if not (src/'cancel_checks/result.json').exists():tasks.append(('cancel',['tools/check_dual_joint_cancel.py']))
 for name,args in tasks:
  if name in a.exclude.split(','):continue
  print('START',a.variant,name,flush=True)
  with (out/(name+'.log')).open('wb') as f:p=subprocess.run([sys.executable,*args,'--variant',a.variant],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=900)
  assert p.returncode==0,(name,(out/(name+'.log')).read_text(errors='replace')[-4000:]);print('PASS',a.variant,name,flush=True)
 print('SUITE_PASS',a.variant,flush=True)
if __name__=='__main__':main()
