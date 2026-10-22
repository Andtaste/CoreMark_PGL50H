"""Prove full EX module equivalence with divider disabled and enabled."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/load_bp_dual_boundary_pcselect';ref=ROOT/'simulation/results/load_bp_dual_boundary_storewrite';out=src/'execute_equivalence';out.mkdir(exist_ok=True);inputs=[Path(__file__).resolve()];tests=[]
 for folder,label in ((ref,'gold'),(src,'gate')):
  p=folder/'nc_execute.v';f=out/(label+'.v');f.write_text(p.read_text().replace('module nc_execute #','module '+label+'_execute #',1));inputs +=[p,f]
 div=ROOT/'hardware/pds/source/core/nc_divide.v';inputs.append(div)
 def linux(p):return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
 for enabled in (0,1):
  script='read_verilog -sv '+' '.join(linux(p) for p in (out/'gold.v',out/'gate.v',div))+f'; chparam -set ENABLE_DIV {enabled} gold_execute; chparam -set ENABLE_DIV {enabled} gate_execute; hierarchy -check; proc; memory; flatten gold_execute gate_execute; async2sync; equiv_make gold_execute gate_execute equiv; hierarchy -top equiv; equiv_simple; equiv_induct -seq 2; equiv_status -assert'
  f=out/f'div{enabled}.ys';f.write_text(script+'\n');inputs.append(f);x=subprocess.run(['wsl.exe','-d','Ubuntu','--','yosys','-p',script],cwd=ROOT,capture_output=True,timeout=300);(out/f'div{enabled}.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0,(x.stdout+x.stderr)[-2500:];tests.append(f'PASS complete actual EX module sequential equivalence, ENABLE_DIV={enabled}, arbitrary packets/controls/prediction/valid/ready/reset/clear, all outputs preserved')
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print('Actual EX equivalence PASS 2')
if __name__=='__main__':main()
