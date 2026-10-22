"""Run integration checks for equivalent forwarding/control mux rewrites."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);ap.add_argument('--collect-only',action='store_true');a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);out=src/'integration_run';out.mkdir(exist_ok=True);tests=[];inputs=[Path(__file__).resolve()]
 jobs=[('pairs','check_dual_boundary_v3.py',['--mode','pairs']),('cancel','check_dual_joint_cancel.py',[]),('audit','check_dual_boundary.py',['--mode','audit']),('protocol','check_dual_joint_reg_protocol.py',[]),('mul_protocol','check_dual_joint_reg_mul_protocol.py',[]),('soc','check_dual_store_simple_soc.py',[]),('uart','check_dual_store_ack.py',['--mode','uart']),('timeline','check_dual_boundary_v3.py',['--mode','timeline'])]
 for label,name,extra in jobs:
  p=ROOT/'tools'/name;inputs.append(p)
  if not a.collect_only:
   x=subprocess.run([sys.executable,str(p),'--variant',a.variant,*extra],cwd=ROOT,capture_output=True,timeout=600);(out/(label+'.log')).write_bytes(x.stdout+x.stderr);assert x.returncode==0,(label,(x.stdout+x.stderr)[-2500:])
  else:assert (out/(label+'.log')).is_file(),label
  tests.append('PASS '+label);print(tests[-1],flush=True)
 ref=ROOT/'simulation/results/load_bp_dual_boundary_storewrite'
 for name,sub in (('nc_memory.v','memory_checks'),('nc_memory.v','posted_module')):
  origin=ref if sub=='posted_module' else ref.with_name('load_bp_dual_boundary_storeack')
  actual=src/name;old=origin/name;ev=origin/sub/'result.json';assert sha(actual)==sha(old) and json.loads(ev.read_text())['status']=='PASS';inputs +=[actual,old,ev];tests.append('PASS unchanged-module hash evidence reuse '+sub)
 receipts={}
 for sub,count in (('pair_checks',6),('cancel_checks',4),('audit_checks',4),('protocol',8),('mul_protocol',4),('posted_soc_final',6),('uart80',1),('timeline_checks',4),('checks',63)):
  p=src/sub/'result.json';x=json.loads(p.read_text());assert x['status']=='PASS' and len(x['tests'])==count,(sub,len(x.get('tests',[])));inputs.append(p);receipts[sub]=count
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,actual_check_counts=receipts,scope='Integration replay on candidate RTL plus explicit exact-hash unchanged MEM test reuse; no board test',input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print('FORWARD integration PASS',a.variant)
if __name__=='__main__':main()
