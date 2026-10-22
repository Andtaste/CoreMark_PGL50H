"""Compare fetch handshakes and visible heads every cycle against the baseline."""
from pathlib import Path
import hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]

def main():
    out=ROOT/'simulation/results/fetch_equiv';out.mkdir(parents=True,exist_ok=True)
    ref=ROOT/'docs/fetch_head/before/source/core/nc_fetch.v'
    reference=out/'old_nc_fetch.v'
    reference.write_text(ref.read_text().replace('module nc_fetch(','module old_nc_fetch(',1))
    iv=shutil.which('iverilog') or str(ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe')
    vvp=shutil.which('vvp') or str(ROOT.parent/'tmp/iverilog-portable/bin/vvp.exe')
    sources=[reference,ROOT/'hardware/pds/source/core/nc_fetch.v',ROOT/'simulation/tb/fetch_equivalence_tb.v']
    subprocess.run([iv,'-g2012','-s','fetch_equivalence_tb','-o',str(out/'sim.vvp'),*map(str,sources)],check=True)
    results=[]
    for seed in (17,91,2026):
        run=subprocess.run([vvp,str(out/'sim.vvp'),f'+seed={seed}'],capture_output=True,timeout=60)
        (out/f'seed_{seed}.log').write_bytes(run.stdout+run.stderr)
        assert run.returncode==0 and b'PASS fetch equivalence cycles=100000' in run.stdout,run.stdout+run.stderr
        results.append({'seed':seed,'status':'PASS','summary':run.stdout.decode().strip()})
        print(results[-1]['summary'])
    (out/'result.json').write_text(json.dumps({'status':'PASS','cycles':300000,'results':results,
        'reference_sha256':hashlib.sha256(ref.read_bytes()).hexdigest(),
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources[1:]}},indent=2))
if __name__=='__main__':main()
