"""Run independent simulations; record failures without hiding candidate evidence."""
from pathlib import Path
import subprocess,sys,json,argparse
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--trials',nargs='+',required=True);ap.add_argument('--phases',nargs='+',default=['smoke','performance']);ap.add_argument('--pds',action='store_true');a=ap.parse_args();records=[]
 for t in a.trials:
  v='dual_boundary_next_'+t;src=ROOT/('simulation/results/load_bp_'+v)
  if not src.exists():subprocess.run([sys.executable,str(ROOT/'tools/generate_dual_next_trials.py'),'--trial',t],cwd=ROOT,check=True)
  for phase in a.phases:
   log=src/('run_'+phase+'.log');print('START',t,phase,flush=True)
   with log.open('wb') as f:x=subprocess.run([sys.executable,str(ROOT/'tools/run_dual_next_trial.py'),'--variant',v,'--phase',phase],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
   records.append(dict(trial=t,phase=phase,exit=x.returncode));print('END',t,phase,x.returncode,flush=True)
   if x.returncode:break
  else:
   if a.pds:
    with (src/'run_pds.log').open('wb') as f:x=subprocess.run([sys.executable,str(ROOT/'tools/research_dual_timing80_pds.py'),'--variant',v],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    records.append(dict(trial=t,phase='pds',exit=x.returncode));print('END',t,'pds',x.returncode,flush=True)
 print(json.dumps(records,indent=2))
if __name__=='__main__':main()
