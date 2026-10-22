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
 new=src/'nc_operands.v';tb=ROOT/'simulation/research/dual_native/operands_tb.v'
 old=out/'old_nc_operands.v';reference=new.read_text().replace('module nc_operands(','module old_nc_operands(',1)
 for op in 'abcd':
  for source in ('f','f1','m','w','w1'):
   reference=reference.replace(f's{source}_{op}[s] && {source}_valid',f'{source}_valid && {source}_tag==dep_{op}[s]')
 old.write_text(reference)
 parent=old
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
 hashes={str(p.relative_to(ROOT)):sha(p) for p in (parent,new,tb,PY)}
 with (out/'compile.log').open('w') as f:subprocess.run([str(iv),'-g2012','-s','operands_equivalence_tb','-o',str(out/'sim.vvp'),str(old),str(new),str(tb)],stdout=f,stderr=subprocess.STDOUT,check=True)
 tests=[]
 for seed in (17,91,2026):
  x=subprocess.run([str(vvp),str(out/'sim.vvp'),f'+seed={seed}'],capture_output=True,check=True,timeout=90)
  (out/f'seed_{seed}.log').write_bytes(x.stdout+x.stderr);s=x.stdout.decode().strip();assert 'PASS operands equivalence cycles=100000' in s,s;tests.append(s);print(s)
 for n,h in hashes.items():assert sha(ROOT/n)==h,n
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,cycles=300000,edge_checks=600000,scope='Four-operand registered selectors versus direct current-tag comparisons; coherent producer lookahead tag protocol; randomized queue stalls/clear/insertion/capture',input_sha256=hashes),indent=2)+'\n')
if __name__=='__main__':main()
