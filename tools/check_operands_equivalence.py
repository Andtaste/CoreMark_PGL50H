"""Cycle-by-cycle operand queue behavior against the newly accepted version."""
from pathlib import Path
import hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def main():
    out=ROOT/'simulation/results/operands_equiv';out.mkdir(parents=True,exist_ok=True)
    ref=ROOT/'docs/ex_id_finish/before/source/core/nc_operands.v';old=out/'old_nc_operands.v'
    old.write_text(ref.read_text().replace('module nc_operands(','module old_nc_operands(',1))
    rtl=ROOT/'hardware/pds/source/core/nc_operands.v';tb=ROOT/'simulation/tb/operands_equivalence_tb.v'
    iv=shutil.which('iverilog') or str(ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe')
    vvp=shutil.which('vvp') or str(ROOT.parent/'tmp/iverilog-portable/bin/vvp.exe')
    inputs=[rtl,tb,ref,Path(__file__).resolve()];hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    with (out/'compile.log').open('w') as f:subprocess.run([iv,'-g2012','-s','operands_equivalence_tb','-o',str(out/'sim.vvp'),str(old),str(rtl),str(tb)],stdout=f,stderr=subprocess.STDOUT,check=True)
    results=[]
    for seed in (17,91,2026):
        x=subprocess.run([vvp,str(out/'sim.vvp'),f'+seed={seed}'],capture_output=True,check=True,timeout=90)
        (out/f'seed_{seed}.log').write_bytes(x.stdout+x.stderr);summary=x.stdout.decode().strip()
        assert 'PASS operands equivalence cycles=100000' in summary,summary
        print(summary);results.append(dict(seed=seed,summary=summary))
    for n,h in hashes.items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,n
    (out/'result.json').write_text(json.dumps(dict(status='PASS',cycles=300000,results=results,input_sha256=hashes),indent=2)+'\n')
if __name__=='__main__':main()
