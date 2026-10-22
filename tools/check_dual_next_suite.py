"""Full integration replay per isolated trial; preserve every failure log."""
from pathlib import Path
import subprocess,sys,json
ROOT=Path(__file__).resolve().parents[1]
for t in sys.argv[1:]:
 v='dual_boundary_next_'+t;src=ROOT/('simulation/results/load_bp_'+v);out=src/'next_suite';out.mkdir(exist_ok=True);records=[]
 jobs=[('checks','run_dual_next_trial.py',['--phase','checks']),('validation','run_dual_next_trial.py',['--phase','validation']),('pairs','check_dual_next_units.py',['--mode','pairs']),('cancel','check_dual_joint_cancel.py',[]),('audit','check_dual_next_units.py',['--mode','audit']),('protocol','check_dual_joint_reg_protocol.py',[]),('mul_protocol','check_dual_joint_reg_mul_protocol.py',[]),('soc','check_dual_next_units.py',['--mode','soc']),('uart','check_dual_store_ack.py',['--mode','uart']),('timeline','check_dual_next_units.py',['--mode','timeline'])]
 for label,tool,extra in jobs:
  print('START',t,label,flush=True)
  with (out/(label+'.log')).open('wb') as f:x=subprocess.run([sys.executable,str(ROOT/'tools'/tool),'--variant',v,*extra],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  records.append(dict(test=label,exit=x.returncode));(out/'progress.json').write_text(json.dumps(records,indent=2)+'\n');print('END',t,label,x.returncode,flush=True)
  if x.returncode:break
 (out/'result.json').write_text(json.dumps(dict(status='PASS' if len(records)==len(jobs) and all(r['exit']==0 for r in records) else 'FAILED',tests=records),indent=2)+'\n')
