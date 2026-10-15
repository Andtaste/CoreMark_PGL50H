"""Run the existing functional checks on the current local-RAM SoC RTL.

Requires Python 3, Icarus Verilog (iverilog/vvp), and GCC for --suite coremark.
Generated firmware, logs and reports stay in ignored simulation directories.
"""
from pathlib import Path
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
SIM = ROOT/'simulation'
SRC = ROOT/'hardware/pds/source'
BUILD = SIM/'firmware/generated/local_ram'
LOGS = SIM/'results/logs/local_ram'
REPORT = SIM/'results/reports/local_ram_regression.json'

def executable(name):
    result = shutil.which(name)
    if result:
        return result
    path = Path(name).resolve()
    if path.is_file():
        return str(path)
    raise RuntimeError(f'Executable not found: {name}')

def command(args, logfile, timeout=120):
    logfile.parent.mkdir(parents=True, exist_ok=True)
    with logfile.open('wb') as stream:
        process = subprocess.Popen([str(a) for a in args], cwd=ROOT,
                                   stdout=stream, stderr=subprocess.STDOUT)
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            stream.write(b'\nHOST_TIMEOUT\n')
            raise
    output = logfile.read_bytes().decode('utf-8', errors='replace')
    if returncode:
        raise RuntimeError(f'Command failed ({returncode}), see {logfile}:\n{output[-2500:]}')
    return output

def image(binary, filename):
    data = binary.read_bytes()
    if not 0 < len(data) <= 65536:
        raise RuntimeError(f'Invalid program image: {binary}')
    data += bytes(65536-len(data))
    filename.write_text(''.join(f'{int.from_bytes(data[i:i+4], "little"):08x}\n'
                              for i in range(0,65536,4)), encoding='ascii')

def compile_soc(iverilog):
    output = BUILD/'soc.vvp'
    files = sorted(p for directory in ('core','sys_bus','perips','debug','utils')
                   for p in (SRC/directory).glob('*.v') if p.name != 'defines.v')
    files += [SRC/'top/tinyriscv_soc_top.v', SIM/'models/memory/pds_ram_models.v',
              SIM/'tb/soc/cpu_bus_soc_tb.v']
    command([iverilog,'-g2012','-s','cpu_bus_soc_tb',
             '-I',SRC/'core','-o',output,*files], LOGS/'compile_soc.log')
    return output

def coremark_binary(gcc):
    gcc = executable(gcc)
    sw = ROOT/'sw'
    cm = sw/'coremark'
    elf = BUILD/'coremark_smoke.elf'
    files = [cm/name for name in ('core_list_join.c','core_main.c','core_matrix.c',
                                 'core_state.c','core_util.c','core_portme.c')]
    files += [sw/name for name in ('start.S','trap_entry.S','init.c','trap_handler.c')]
    files += [sw/'lib'/name for name in ('utils.c','xprintf.c','uart.c')]
    command([gcc,'-O2','-mcmodel=medlow','-march=rv32im_zicsr','-mabi=ilp32',
             '-ffunction-sections','-fdata-sections','-fno-builtin-printf','-fno-builtin-malloc',
             '-DITERATIONS=1','-I',cm,'-I',sw,'-I',sw/'include',*files,
             '-T',sw/'link.lds','-nostartfiles','-Wl,--gc-sections','-o',elf],LOGS/'coremark_build.log')
    objcopy = str(Path(gcc).with_name(Path(gcc).name.replace('gcc','objcopy')))
    binary = BUILD/'coremark_smoke.bin'
    command([objcopy,'-O','binary',elf,binary],LOGS/'coremark_objcopy.log')
    nm = str(Path(gcc).with_name(Path(gcc).name.replace('gcc','nm')))
    symbols = command([nm,elf],LOGS/'coremark_symbols.log')
    match = re.search(r'^([0-9a-fA-F]+)\s+\w\s+loop\s*$',symbols,re.MULTILINE)
    if not match: raise RuntimeError('CoreMark exit loop symbol not found')
    (BUILD/'coremark_finish_pc.txt').write_text(match[1],encoding='ascii')
    return binary

def ram2_binary(gcc, source=None):
    gcc = executable(gcc)
    source = source or SIM/'tests/bus/memory/ram2_parallel.S'
    elf = BUILD/(source.stem+'.elf')
    command([gcc,'-march=rv32im_zicsr','-mabi=ilp32','-nostdlib',
             '-Wl,-Ttext=0','-Wl,--build-id=none',
             source,'-o',elf],LOGS/(source.stem+'_build.log'))
    objcopy = str(Path(gcc).with_name(Path(gcc).name.replace('gcc','objcopy')))
    binary = BUILD/(source.stem+'.bin')
    command([objcopy,'-O','binary',elf,binary],LOGS/(source.stem+'_objcopy.log'))
    return binary

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iverilog', default='iverilog')
    parser.add_argument('--vvp', default='vvp')
    parser.add_argument('--gcc', default='riscv-none-elf-gcc')
    parser.add_argument('--suite', choices=['unit','isa','data','pipeline','coremark','all'], default='pipeline')
    parser.add_argument('--coremark-timeout', type=int, default=1800,
                        help='Host timeout in seconds for each CoreMark functional smoke run')
    args = parser.parse_args()
    iv, vvp = executable(args.iverilog), executable(args.vvp)
    BUILD.mkdir(parents=True,exist_ok=True)
    LOGS.mkdir(parents=True,exist_ok=True)
    results = []
    if args.suite in ('pipeline','all'):
        stats = BUILD/'stat_pipeline.vvp'
        command([iv,'-g2012','-s','stat_pipeline_tb','-I',SRC/'core',
                 '-o',stats,SRC/'core/csr_reg.v',SIM/'tb/unit/csr/stat_pipeline_tb.v'],
                LOGS/'compile_stat_pipeline.log')
        output = command([vvp,stats],LOGS/'stat_pipeline.log')
        if 'TEST_PASS STAT_PIPELINE' not in output: raise RuntimeError('No statistics PASS marker')
        print(output.strip(),flush=True)
        results.append({'name':'statistics_event_pipeline','status':'PASS'})
        frontend = BUILD/'ifu_fifo.vvp'
        command([iv,'-g2012','-s','ifu_fifo_tb','-I',SRC/'core',
                 '-o',frontend,SRC/'core/ifu.v',SIM/'tb/unit/ifu_fifo_tb.v'],
                LOGS/'compile_ifu_fifo.log')
        output = command([vvp,frontend],LOGS/'ifu_fifo.log')
        if 'TEST_PASS IFU_FIFO' not in output: raise RuntimeError('No frontend PASS marker')
        print(output.strip(),flush=True)
        results.append({'name':'ifu_fifo_protocol','status':'PASS'})
    if args.suite in ('unit','all'):
        owner = BUILD/'ram_owner.vvp'
        command([iv,'-g2012','-s','rib_owner_tb','-o',owner,
                 SRC/'sys_bus/local_ram_bus.v',SIM/'tb/unit/bus/rib_owner_tb.v'],
                LOGS/'compile_owner.log')
        output = command([vvp,owner],LOGS/'owner.log')
        if 'TEST_PASS RIB_OWNER' not in output: raise RuntimeError('No owner PASS marker')
        print(output.strip(),flush=True)
        results.append({'name':'local_ram_owner','status':'PASS','cases':6})
    if args.suite in ('isa','data','pipeline','coremark','all'):
        fixtures = sorted((ROOT/'references/tinyriscv/tests/isa/generated').glob('*.bin')) if args.suite in ('isa','all') else []
        fixtures = [p for p in fixtures if p.name.startswith(('rv32ui-','rv32um-'))]
        if args.suite in ('isa','all') and not fixtures: raise RuntimeError('No ISA fixtures found')
        if args.suite in ('coremark','all'):
            fixtures.append(coremark_binary(args.gcc))
        if args.suite in ('data','all'):
            fixtures.append(ram2_binary(args.gcc))
        if args.suite in ('pipeline','all'):
            fixtures.append(ram2_binary(args.gcc,SIM/'tests/pipeline/five_stage_hazards.S'))
        program = compile_soc(iv)
        for binary in fixtures:
            hexfile = BUILD/(binary.stem+'.hex')
            image(binary,hexfile)
            is_coremark = binary.name=='coremark_smoke.bin'
            extra = ['+finish_pc='+(BUILD/'coremark_finish_pc.txt').read_text('ascii')] if is_coremark else []
            output = command([vvp,program,f'+image={hexfile}',
                              '+limit='+('3000000' if is_coremark else '250000'),
                              f'+coremark={int(is_coremark)}',*extra],LOGS/f'{binary.stem}.log',
                             timeout=args.coremark_timeout if is_coremark else 120)
            if 'TEST_PASS' not in output: raise RuntimeError(f'No PASS: {binary.name}')
            if is_coremark:
                for label,value in [('seedcrc','e9f5'),('crclist','e714'),('crcmatrix','1fd7'),('crcstate','8e3a'),('crcfinal','e714')]:
                    if not re.search(label+r'\s*:\s*0x'+value,output):
                        raise RuntimeError(f'CoreMark {label} mismatch')
            cycles = int(re.search(r'TEST_PASS cycles=(\d+)', output)[1])
            item = {'name':binary.stem,'cycles':cycles,'status':'PASS'}
            grants = re.search(r'parallel_grants=(\d+)',output)
            if grants:
                item['parallel_grants'] = int(grants[1])
            if binary.name=='ram2_parallel.bin' and not item.get('parallel_grants'):
                raise RuntimeError('No simultaneous fetch/data requests observed')
            if is_coremark:
                item['benchmark_cycles'] = int(re.search(r'Benchmark cycles64\s*:\s*(\d+)',output)[1])
            results.append(item)
            print(item,flush=True)
        if args.suite in ('pipeline','all'):
            latency = BUILD/'cpu_latency.vvp'
            files = sorted(p for p in (SRC/'core').glob('*.v') if p.name!='defines.v')
            files += sorted((SRC/'utils').glob('*.v'))
            command([iv,'-g2012','-s','cpu_latency_tb','-I',SRC/'core',
                     '-o',latency,*files,SIM/'tb/soc/cpu_latency_tb.v'],LOGS/'compile_latency.log')
            output = command([vvp,latency,'+image='+str(BUILD/'five_stage_hazards.hex')],LOGS/'latency.log')
            if 'TEST_PASS LATENCY' not in output: raise RuntimeError('No latency PASS marker')
            results.append({'name':'five_stage_variable_latency','status':'PASS',
                            'cycles':int(re.search(r'LATENCY cycles=(\d+)',output)[1])})
            print(output.strip(),flush=True)
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    report = REPORT.with_name('local_ram_regression_'+args.suite+'.json')
    report.write_text(json.dumps({'suite':args.suite,'scope':'Functional synchronous RAM models; no FPGA timing verification',
                                  'results':results},indent=2)+'\n',encoding='utf-8')
    print(f'PASS: {len(results)} runs; report: {report}',flush=True)

if __name__=='__main__':
    try:
        main()
    except (RuntimeError,OSError,subprocess.TimeoutExpired) as exc:
        print(f'FAIL: {exc}',file=sys.stderr)
        sys.exit(1)
