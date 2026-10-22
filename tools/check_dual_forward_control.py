"""Prove actual whole operand boundary, including unavailable-cycle values."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);ref=ROOT/'simulation/results/load_bp_dual_boundary_storewrite';out=src/'forward_equivalence';out.mkdir(exist_ok=True);inputs=[Path(__file__).resolve()]
 for folder,label in ((ref,'gold'),(src,'gate')):
  p=folder/'nc_operands.v';f=out/(label+'.v');f.write_text(p.read_text().replace('module nc_operands(','module '+label+'_operands(',1));inputs +=[p,f]
 def linux(p):return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
 script='read_verilog -sv '+linux(out/'gold.v')+' '+linux(out/'gate.v')+'; proc; memory; async2sync; equiv_make gold_operands gate_operands equiv; hierarchy -top equiv; equiv_simple; equiv_induct -seq 2; equiv_status -assert'
 (out/'run.ys').write_text(script+'\n');x=subprocess.run(['wsl.exe','-d','Ubuntu','--','yosys','-p',script],cwd=ROOT,capture_output=True,timeout=300);(out/'proof.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0,(x.stdout+x.stderr)[-3000:]
 inputs.append(out/'run.ys');(out/'result.json').write_text(json.dumps(dict(status='PASS',tests=['PASS whole actual operand boundary sequential equivalence, original priority even conflicting broadcasts, stalls/clear/reset/insertion and invalid-cycle output values; no producer-consistency assumptions'],input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print(a.variant,'full operand equivalence PASS')
if __name__=='__main__':main()
