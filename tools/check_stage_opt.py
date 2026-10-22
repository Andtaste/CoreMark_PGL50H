"""Check memory turnover ownership, request stability and precise faults."""
from pathlib import Path
import subprocess,sys,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'simulation/scripts/run'))
from regression import find,run

def main():
    out=ROOT/'simulation/results/stage_opt';out.mkdir(parents=True,exist_ok=True)
    iv=find('iverilog',[ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe'])
    vvp=find('vvp',[ROOT.parent/'tmp/iverilog-portable/bin/vvp.exe'])
    sources=[ROOT/'hardware/pds/source/core/nc_memory.v',ROOT/'simulation/tb/memory_turnover_tb.v']
    run([iv,'-g2012','-s','memory_turnover_tb','-o',out/'memory.vvp',*sources],out/'memory_iverilog_compile.log')
    log=run([vvp,out/'memory.vvp'],out/'memory_iverilog.log');assert 'rounds=128' in log,log
    def linux(p):
        p=Path(p).resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
    prefix=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--']
    with (out/'memory_verilator_compile.log').open('w') as f:
        subprocess.run([*prefix,'verilator','--binary','--timing','-j','4','-Wno-fatal','--top-module','memory_turnover_tb','--Mdir',linux(out/'memory_obj'),*[linux(p) for p in sources]],stdout=f,stderr=subprocess.STDOUT,check=True)
    with (out/'memory_verilator.log').open('w') as f:subprocess.run([*prefix,linux(out/'memory_obj/Vmemory_turnover_tb')],stdout=f,stderr=subprocess.STDOUT,check=True)
    log=(out/'memory_verilator.log').read_text(encoding='utf-8',errors='replace');assert 'rounds=128' in log,log
    overlap=[sources[0],ROOT/'simulation/tb/memory_overlap_tb.v']
    run([iv,'-g2012','-s','memory_overlap_tb','-o',out/'memory_overlap.vvp',*overlap],out/'memory_overlap_iverilog_compile.log')
    log=run([vvp,out/'memory_overlap.vvp'],out/'memory_overlap_iverilog.log');assert 'PASS memory overlap cycles=14000' in log,log
    with (out/'memory_overlap_verilator_compile.log').open('w') as f:
        subprocess.run([*prefix,'verilator','--binary','--timing','-j','4','-Wno-fatal','--top-module','memory_overlap_tb','--Mdir',linux(out/'memory_overlap_obj'),*[linux(p) for p in overlap]],stdout=f,stderr=subprocess.STDOUT,check=True)
    with (out/'memory_overlap_verilator.log').open('w') as f:subprocess.run([*prefix,linux(out/'memory_overlap_obj/Vmemory_overlap_tb')],stdout=f,stderr=subprocess.STDOUT,check=True)
    log=(out/'memory_overlap_verilator.log').read_text(encoding='utf-8',errors='replace');assert 'PASS memory overlap cycles=14000' in log,log
    result=dict(status='PASS',rounds_per_simulator=128,overlap_cycles_per_simulator=14000,simulators=['Icarus','Verilator'],source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[overlap[1],Path(__file__).resolve()]})
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
