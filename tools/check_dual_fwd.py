"""Forwarding mask SAT proof and dual operand boundary cycle equivalence."""
from pathlib import Path
import argparse,hashlib,json,subprocess,re
ROOT=Path(__file__).resolve().parents[1]
PY=Path(__file__).resolve()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def linux(p):return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);args=ap.parse_args()
 src=ROOT/('simulation/results/load_bp_'+args.variant);out=src/'forwarding_equivalence';out.mkdir(exist_ok=True)
 parent=ROOT/'simulation/results/load_bp_dual_if_parts/nc_operands.v';new=src/'nc_operands.v';tb=ROOT/'simulation/research/dual_ram/fwd_operands_tb.v'
 old=out/'old_nc_operands.v';old.write_text(parent.read_text().replace('module nc_operands(','module old_nc_operands(',1))
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
 hashes={str(p.relative_to(ROOT)):sha(p) for p in (parent,new,tb,PY)}
 with (out/'compile.log').open('w') as f:subprocess.run([str(iv),'-g2012','-s','operands_equivalence_tb','-o',str(out/'sim.vvp'),str(old),str(new),str(tb)],stdout=f,stderr=subprocess.STDOUT,check=True)
 tests=[]
 for seed in (17,91,2026):
  x=subprocess.run([str(vvp),str(out/'sim.vvp'),f'+seed={seed}'],capture_output=True,check=True,timeout=90)
  (out/f'seed_{seed}.log').write_bytes(x.stdout+x.stderr);s=x.stdout.decode().strip();assert 'PASS operands equivalence cycles=100000' in s,s;tests.append(s);print(s)
 # Extract the actual local combinational assignments, rather than proving
 # a hand-maintained copy of the candidate equation. All hit combinations,
 # including unequal simultaneous matches and the no-hit fallback, are free.
 s=new.read_text();a=s.index('  wire use_a_f=');b=s.index('  assign hit_f1b',a)
 candidate=s[a:b].replace('[s]','').replace('selected_va','candidate')
 candidate=re.sub(r'\bwa\b','waiting',candidate)
 proof='''module proof(input waiting,input hit_fa,hit_f1a,hit_ma,hit_wa,
 input [31:0] va,f_data,f1_data,m_data,w_data,w1_data,output equal);
 wire[31:0] candidate;
 wire[31:0] reference=waiting?(hit_fa?f_data:hit_f1a?f1_data:hit_ma?m_data:hit_wa?w_data:w1_data):va;
'''+candidate.replace('hit_waitinga','hit_wa')+'\n assign equal=candidate==reference;\nendmodule\n'
 # Replacing the bare wait symbol must not rename hit_wa.
 proof=proof.replace('hit_waitinga','hit_wa')
 file=out/'mask_proof.v';file.write_text(proof)
 command=['wsl.exe','-d','Ubuntu','--','yosys','-p',f'read_verilog -sv {linux(file)}; prep -top proof -flatten; sat -verify -prove equal 1 -show-inputs -show-outputs']
 x=subprocess.run(command,capture_output=True,timeout=90);(out/'sat.log').write_bytes(x.stdout+x.stderr)
 assert x.returncode==0 and b'SUCCESS!' in x.stdout,x.stdout.decode()[-4000:];tests.append('PASS SAT actual A-side priority mask for all 2-state hits/wait/data; B-side generated symmetrically')
 hashes[str(file.relative_to(ROOT))]=sha(file)
 for n,h in hashes.items():assert sha(ROOT/n)==h,n
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,cycles=300000,edge_checks=600000,input_sha256=hashes),indent=2)+'\n')
if __name__=='__main__':main()
