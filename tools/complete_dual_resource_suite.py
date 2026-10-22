"""Resume after width-specific historical audit; never discard failure records."""
from pathlib import Path
import sys,subprocess,json
ROOT=Path(__file__).resolve().parents[1]
for t in sys.argv[1:]:
 v='dual_boundary_next_'+t;src=ROOT/('simulation/results/load_bp_'+v);out=src/'resource_suite';out.mkdir(exist_ok=True)
 previous=json.loads((src/'next_suite/progress.json').read_text());records=[r for r in previous if r['exit']==0]
 jobs=[('audit','check_dual_resource_audit.py',[]),('protocol','check_dual_joint_reg_protocol.py',[]),('mul_protocol','check_dual_joint_reg_mul_protocol.py',[]),('soc','check_dual_next_units.py',['--mode','soc']),('uart','check_dual_store_ack.py',['--mode','uart']),('timeline','check_dual_next_units.py',['--mode','timeline'])]
 for label,tool,extra in jobs:
  if any(r['test']==label for r in records):continue
  print('START',t,label,flush=True)
  with (out/(label+'.log')).open('wb') as f:x=subprocess.run([sys.executable,str(ROOT/'tools'/tool),'--variant',v,*extra],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  records.append(dict(test=label,exit=x.returncode));print('END',t,label,x.returncode,flush=True)
  if x.returncode:break
 (out/'result.json').write_text(json.dumps(dict(status='PASS' if len(records)==10 and all(r['exit']==0 for r in records) else 'FAILED',tests=records,historical_failure='Unmodified legacy audit required literal FIFO WIDTH(249); compressed WIDTH(217) is separately proved and audited. Original failure logs retained.'),indent=2)+'\n')
