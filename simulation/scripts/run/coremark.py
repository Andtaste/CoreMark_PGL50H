"""Cycle-accurate SoC + synchronous RAM; accelerate only UART outside timing."""
from pathlib import Path
import argparse,json,re,subprocess,sys,hashlib
from regression import ROOT,OUT,find
def main():
    p=argparse.ArgumentParser();p.add_argument('--iterations',type=int,default=1)
    p.add_argument('--validation',action='store_true')
    p.add_argument('--verilator',action='store_true',help='Use installed WSL Ubuntu Verilator')
    p.add_argument('--no-build',action='store_true',help='Run the existing image unchanged')
    p.add_argument('--no-bp',action='store_true',help='Simulation-only ENABLE_BP=0 override for comparison')
    p.add_argument('--result-tag',default='',help='Keep an optimization measurement in its own directory')
    a=p.parse_args()
    opts=['--iterations',str(a.iterations)]+(['--validation'] if a.validation else [])
    if not a.no_build:subprocess.run([sys.executable,str(ROOT/'tools/build_coremark.py'),*opts],check=True)
    name=f'coremark_{"validation" if a.validation else "performance"}_{a.iterations}'
    if a.result_tag and not re.fullmatch(r'[A-Za-z0-9_-]+',a.result_tag):p.error('invalid result tag')
    out=OUT/(name+('_verilator' if a.verilator else '')+('_no_bp' if a.no_bp else '')+('_'+a.result_tag if a.result_tag else ''));out.mkdir(parents=True,exist_ok=True)
    image=ROOT/'sw/build'/name/'coremark.hex'
    iv=find('iverilog',[ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe'])
    vvp=find('vvp',[ROOT.parent/'tmp/iverilog-portable/bin/vvp.exe'])
    rtl=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[])
    models=[ROOT/'simulation/models/pango_ram_models.v',ROOT/'simulation/tb/soc_tb.v']
    input_hashes={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in rtl+models+[image]}
    compile_rtl=rtl
    if a.no_bp:
        source=ROOT/'hardware/pds/source/core/nc_core.v';text=source.read_text()
        assert 'parameter ENABLE_BP=1' in text
        replacement=out/'nc_core_no_bp.v'
        replacement.write_text(text.replace('parameter ENABLE_BP=1','parameter ENABLE_BP=0',1))
        compile_rtl=[replacement if x==source else x for x in rtl]
    if a.verilator:
        def linux(path):
            path=Path(path).resolve()
            return '/mnt/'+path.drive[0].lower()+path.as_posix()[2:]
        prefix=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--']
        # Verilator 5.032 lacks hierarchical defparam support. Make explicit
        # simulation-only copies with the identical UART divider override.
        uart_source=ROOT/'hardware/pds/source/perips/nc_uart.v'
        uart_sim=out/'nc_uart_sim.v';tb_sim=out/'soc_tb_sim.v'
        uart_sim.write_text(uart_source.read_text().replace('BAUD=115200','BAUD=9375000'))
        tb_sim.write_text(models[-1].read_text().replace(' defparam dut.bus.uart.BAUD=9375000;',''))
        compile_sources=[x for x in compile_rtl if x!=uart_source]+[uart_sim,models[0],tb_sim]
        with (out/'compile.log').open('w') as f:
            subprocess.run([*prefix,'verilator','--binary','--timing','-j','4','-Wno-fatal',
                            '-DCOREMARK_SIM','--top-module','soc_tb','--Mdir',linux(out/'obj'),
                            *[linux(x) for x in compile_sources]],stdout=f,stderr=subprocess.STDOUT,check=True)
        command=[*prefix,linux(out/'obj/Vsoc_tb'),f'+image={linux(image)}',
                 f'+trace={linux(out)}/retire.trace',f'+uart={linux(out)}/uart.txt']
    else:
        subprocess.run([iv,'-g2012','-Wall','-DCOREMARK_SIM','-s','soc_tb','-o',str(out/'sim.vvp'),
                        *map(str,compile_rtl+models)],check=True)
        command=[vvp,str(out/'sim.vvp'),f'+image={image}',f'+trace={out}/retire.trace',f'+uart={out}/uart.txt']
    with (out/'simulation.log').open('w') as f:
        subprocess.run([*command,'+notrace=1',f'+limit={3000000+a.iterations*3000000}'],
                       cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=3600)
    uart=(out/'uart.txt').read_text();log=(out/'simulation.log').read_text(encoding='utf-8',errors='replace')
    assert 'PASS cycles=' in log,log
    assert 'COUNTER_CHECK_PASS' in log,log
    assert 'CRC validation   : PASS' in uart,uart
    expected=('18f2','e3c1','0747','8d84') if a.validation else ('e9f5','e714','1fd7','8e3a')
    for key,value in zip(('seedcrc','crclist','crcmatrix','crcstate'),expected):
        assert re.search(key+r'\s*: 0x'+value,uart),uart
    assert 'Stats overflow mask: 0x0000' in uart,uart
    metrics={}
    for line in uart.splitlines():
        if ':' in line:
            k,v=line.split(':',1);metrics[k.strip()]=v.strip()
    cycles=int(metrics['Stats window cycles']);retired=int(metrics['Retired instructions'])
    assert 0<retired<=cycles
    assert float(metrics['IPC'])<=retired/cycles<float(metrics['IPC'])+0.0011
    for filename,digest in input_hashes.items():
        assert hashlib.sha256((ROOT/filename).read_bytes()).hexdigest()==digest,'Input changed during simulation: '+filename
    result={'status':'PASS','scope':'RTL diagnostic; UART divisor 8 only outside measurement; no board measurement',
            'metrics':metrics,'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),
            'rtl_sha256':{str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in rtl}}
    result['input_sha256']=input_hashes
    result['configuration']={'ENABLE_BP':0 if a.no_bp else 1,'simulation_only_parameter_override':a.no_bp}
    if a.no_bp:result['configuration']['override_sha256']=hashlib.sha256(replacement.read_bytes()).hexdigest()
    bp=re.search(r'PREDICTOR_STATS ([^\r\n]+)',log)
    if bp:
        result['predictor']={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',bp[1])}
        result['predictor']['next_pc_accuracy']=1-result['predictor']['next_pc_wrong']/max(1,result['predictor']['resolved'])
        result['predictor']['legacy_firmware_footer']='Unchanged image says No BTB; use enabled and predictor metrics for actual hardware configuration.'
    mul=re.search(r'MULTIPLY_STATS ([^\r\n]+)',log)
    if mul:result['multiply']={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',mul[1])}
    (out/'result.json').write_text(json.dumps(result,indent=2))
    print(uart);print('\n'.join(line for line in log.splitlines() if 'PASS' in line or 'PREDICTOR_STATS' in line or 'MULTIPLY_STATS' in line));print('COREMARK_PASS',out,flush=True)
if __name__=='__main__':main()
