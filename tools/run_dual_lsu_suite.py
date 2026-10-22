"""Finish isolated LSU checks without replacing existing evidence."""
from pathlib import Path
import json, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[1]
def main():
 out=ROOT/'simulation/results/dual_lsu_suite';out.mkdir(exist_ok=True)
 records=[]
 for variant in ('dual_lsu_shared','dual_lsu_ports','dual_lsu_forward','dual_lsu_pair'):
  src=ROOT/('simulation/results/load_bp_'+variant)
  for mode in ('extra','pairs','bus','directed','stats','audit','operands','cancel'):
   folder={'extra':'dual_checks','pairs':'pair_checks','cancel':'cancel_checks'}.get(mode,mode+'_checks')
   result=src/folder/'result.json'
   if result.exists() and json.loads(result.read_text()).get('status')=='PASS':
    records.append(dict(variant=variant,mode=mode,status='EXISTING_PASS'));continue
   cmd=[sys.executable,str(ROOT/'tools'/('check_dual_joint_cancel.py' if mode=='cancel' else 'check_dual_lsu.py')),'--variant',variant]
   if mode!='cancel':cmd+=['--mode',mode]
   start=time.time()
   p=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=1200)
   (out/(variant+'_'+mode+'.log')).write_bytes(p.stdout+p.stderr)
   records.append(dict(variant=variant,mode=mode,status='PASS' if p.returncode==0 else 'FAIL',seconds=time.time()-start))
   (out/'result.json').write_text(json.dumps(records,indent=2)+'\n')
   print(variant,mode,records[-1]['status'],flush=True)
 (out/'result.json').write_text(json.dumps(records,indent=2)+'\n')
 assert all(r['status']!='FAIL' for r in records)
if __name__=='__main__':main()
