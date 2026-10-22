"""Check EX packet and redirect decisions against the archived pre-change RTL."""
from pathlib import Path
import hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def main():
    out=ROOT/'simulation/results/ex_equiv';out.mkdir(parents=True,exist_ok=True)
    ref=ROOT/'docs/ex_timing/before/hardware/pds/source/core/nc_execute.v'
    reference=out/'old_nc_execute.v'
    reference.write_text(ref.read_text().replace('module nc_execute(','module old_nc_execute(',1))
    prior=ROOT/'docs/fetch_head/before/source/core/nc_execute.v'
    prior_source=out/'prior_nc_execute.v'
    prior_source.write_text(prior.read_text().replace('module nc_execute(','module prior_nc_execute(',1))
    iv=shutil.which('iverilog') or str(ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe')
    vvp=shutil.which('vvp') or str(ROOT.parent/'tmp/iverilog-portable/bin/vvp.exe')
    sources=[reference,prior_source,ROOT/'docs/mul_pipeline/before/source/core/nc_muldiv.v',
             *[ROOT/'hardware/pds/source/core'/f for f in ('nc_execute.v','nc_decode.v','nc_divide.v')],
             ROOT/'simulation/tb/execute_equivalence_tb.v']
    subprocess.run([iv,'-g2012','-s','execute_equivalence_tb','-o',str(out/'sim.vvp'),*map(str,sources)],check=True)
    result=subprocess.run([vvp,str(out/'sim.vvp')],capture_output=True,check=True,timeout=60)
    (out/'result.log').write_bytes(result.stdout+result.stderr)
    text=result.stdout.decode(errors='replace')
    assert 'PASS execute equivalence vectors=24000' in text,text
    assert 'PASS execute fault-priority equivalence vectors=8000' in text,text
    assert 'PASS execute prediction checks=12000' in text,text
    assert 'PASS execute memory-aux checks=44000' in text,text
    (out/'result.json').write_text(json.dumps({'status':'PASS','summary':text.strip(),
        'reference_sha256':hashlib.sha256(ref.read_bytes()).hexdigest(),
        'immediate_baseline_sha256':hashlib.sha256(prior.read_bytes()).hexdigest(),
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources[1:]}},indent=2))
    print(text.strip())
if __name__=='__main__':main()
