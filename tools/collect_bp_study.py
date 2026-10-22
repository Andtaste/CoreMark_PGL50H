"""Collect old-state lookup / registered training events from accepted RTL."""
from pathlib import Path
import gzip,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def linux(p):
    p=Path(p).resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def main():
    out=ROOT/'simulation/results/bp_study_trace';out.mkdir(parents=True,exist_ok=True)
    accepted=ROOT/'docs/accepted_baseline.json';b=json.loads(accepted.read_text());preserve={p:sha(p) for p in (accepted,ROOT/'hardware/pds/report_timing/top.rtr')}
    for n,h in b['source_sha256'].items():assert sha(ROOT/n)==h,n
    rtl=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[])
    uart_src=ROOT/'hardware/pds/source/perips/nc_uart.v';source_tb=ROOT/'simulation/tb/soc_tb.v';model=ROOT/'simulation/models/pango_ram_models.v';obs=ROOT/'simulation/research/bp_study_trace.vh';image=ROOT/'sw/build/coremark_performance_10/coremark.hex'
    inputs=rtl+[source_tb,model,obs,image,Path(__file__).resolve()];hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    uart=out/'nc_uart_sim.v';uart.write_text(uart_src.read_text().replace('BAUD=115200','BAUD=9375000'))
    tb=out/'soc_tb_sim.v';tb.write_text(source_tb.read_text().replace('reg[1023:0]','reg[4095:0]').replace(' defparam dut.bus.uart.BAUD=9375000;','').replace('endmodule',obs.read_text()+'\nendmodule'))
    actual=[p for p in rtl if p!=uart_src]+[uart,model,tb];prefix=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--']
    def run(cmd,name):
        with (out/name).open('w') as f:x=subprocess.run(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=600)
        assert x.returncode==0,(name,(out/name).read_text(errors='replace')[-3000:])
    run([*prefix,'verilator','--binary','--timing','-j','4','-Wno-fatal','-DCOREMARK_SIM','--top-module','soc_tb','--Mdir',linux(out/'obj'),*[linux(p) for p in actual]],'compile.log')
    run([*prefix,linux(out/'obj/Vsoc_tb'),f'+image={linux(image)}',f'+trace={linux(out)}/unused.trace',f'+bp_events={linux(out)}/events.txt',f'+uart={linux(out)}/uart.txt','+notrace=1','+limit=33000000'],'simulation.log')
    log=(out/'simulation.log').read_text(errors='replace');u=(out/'uart.txt').read_text()
    assert 'COUNTER_CHECK_PASS cycles=3605011 retired=2808261 loads=548709 stores=143410' in log and 'CRC validation   : PASS' in u
    result=dict(status='PASS',cycles=3605011,retired=2808261,input_sha256=hashes,actual_compile_sha256={str(p.relative_to(ROOT)):sha(p) for p in actual},image_sha256=sha(image),preserved_sha256={str(p.relative_to(ROOT)):h for p,h in preserve.items()})
    m=re.search(r'PREDICTOR_STATS ([^\r\n]+)',log);result['predictor']={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])}
    for n,h in hashes.items():assert sha(ROOT/n)==h,n
    for p,h in preserve.items():assert sha(p)==h,p
    with (out/'events.txt').open('rb') as f,gzip.open(out/'events.txt.gz','wb',compresslevel=6) as g:
        for block in iter(lambda:f.read(1<<20),b''):g.write(block)
    (out/'events.txt').unlink()
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if not k.endswith('sha256')},indent=2))
if __name__=='__main__':main()
