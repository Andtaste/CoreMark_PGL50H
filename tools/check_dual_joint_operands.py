"""Check compact side-field capture against separate four-value reference storage."""
from pathlib import Path
import argparse,hashlib,json,subprocess,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);out=src/'operand_checks';out.mkdir(exist_ok=True)
 golden=ROOT/'simulation/research/dual_native/nc_operands.v';tb_source=ROOT/'simulation/research/dual_native/operands_tb.v'
 s=golden.read_text().replace('module nc_operands(','module old_nc_operands(',1)
 for op in 'abcd':
  for producer in ['f','f1','m','w','w1']:
   s=s.replace(f's{producer}_{op}[s] && {producer}_valid',f'{producer}_valid && {producer}_tag==dep_{op}[s]')
 ref=out/'reference.v';ref.write_text(s)
 tb=out/'operands_tb.v';s=tb_source.read_text();pos=s.index(' old_nc_operands ref_dut')
 s=s[:pos].replace('.next_f_tag(next_f_tag),.next_m_tag(next_m_tag),.next_w_tag(next_w_tag),','')+s[pos:]
 tb.write_text(s)
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe');actual=src/'nc_operands.v'
 inputs=[golden,tb_source,ref,tb,actual,Path(__file__).resolve()]
 p=subprocess.run([str(iv),'-g2012','-s','operands_equivalence_tb','-o',str(out/'sim.vvp'),str(actual),str(ref),str(tb)],capture_output=True,timeout=90);(out/'compile.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stderr.decode(errors='replace')
 tests=[]
 for seed in [17,91,2026]:
  p=subprocess.run([str(vvp),str(out/'sim.vvp'),f'+seed={seed}'],capture_output=True,timeout=120);(out/f'seed_{seed}.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stdout.decode(errors='replace');s=p.stdout.decode();assert 'PASS operands equivalence cycles=100000' in s;tests.append(s.strip())
 x=dict(status='PASS',tests=tests,cycles=300000,edge_checks=600000,scope='Random stalls/clear/insertion/multi-hit priority; independent separate side-value storage with direct current tag comparisons versus compact packet field capture; not whole-core formal proof',input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs})
 (out/'result.json').write_text(json.dumps(x,indent=2)+'\n');print('\n'.join(tests))
if __name__=='__main__':main()
