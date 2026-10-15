"""Check per-slave arbitration and run RV32IM programs on the current SoC RTL.

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
BUILD = SIM/'firmware/generated/bus_regression'
LOGS = SIM/'results/logs/bus_regression'
REPORT = SIM/'results/reports/bus_regression.json'

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

def compile_soc(iverilog, mode):
    output = BUILD/f'soc_{mode}.vvp'
    files = sorted(p for directory in ('core','sys_bus','perips','debug','utils')
                   for p in (SRC/directory).glob('*.v') if p.name != 'defines.v')
    files += [SRC/'top/tinyriscv_soc_top.v', SIM/'models/memory/pds_ram_models.v',
              SIM/'tb/soc/cpu_bus_soc_tb.v']
    command([iverilog,'-g2012','-s','cpu_bus_soc_tb',
             '-P',f'cpu_bus_soc_tb.PARALLEL_ACCESS={mode}',
             '-I',SRC/'core','-o',output,*files], LOGS/f'compile_soc_{mode}.log')
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

def ram2_binary(gcc):
    gcc = executable(gcc)
    elf = BUILD/'ram2_parallel.elf'
    command([gcc,'-march=rv32im_zicsr','-mabi=ilp32','-nostdlib',
             '-Wl,-Ttext=0','-Wl,--build-id=none',
             SIM/'tests/bus/memory/ram2_parallel.S','-o',elf],LOGS/'ram2_build.log')
    objcopy = str(Path(gcc).with_name(Path(gcc).name.replace('gcc','objcopy')))
    binary = BUILD/'ram2_parallel.bin'
    command([objcopy,'-O','binary',elf,binary],LOGS/'ram2_objcopy.log')
    return binary

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iverilog', default='iverilog')
    parser.add_argument('--vvp', default='vvp')
    parser.add_argument('--gcc', default='riscv-none-elf-gcc')
    parser.add_argument('--suite', choices=['unit','isa','data','coremark','all'], default='all')
    args = parser.parse_args()
    iv, vvp = executable(args.iverilog), executable(args.vvp)
    BUILD.mkdir(parents=True,exist_ok=True)
    LOGS.mkdir(parents=True,exist_ok=True)
    results = []
    if args.suite in ('unit','all'):
        old = ROOT/'references/pgl22g/source/sys_bus/rib.v'
        baseline = BUILD/'rib_baseline.v'
        baseline_text = old.read_text('utf-8').replace('module rib #(', 'module rib_baseline #(',1)
        # The archived RTL shares integer j between two combinational blocks.
        # Split only these simulation loop indices; the mux equations are unchanged.
        baseline_text = baseline_text.replace('begin: m_out', 'begin: m_out\n        integer j;')
        baseline_text = baseline_text.replace('begin: s_out', 'begin: s_out\n        integer j;')
        baseline.write_text(baseline_text, encoding='utf-8')
        unit = BUILD/'rib_unit.vvp'
        command([iv,'-g2012','-s','rib_arb_tb','-o',unit,SRC/'sys_bus/rib.v',
                 baseline,SIM/'tb/unit/bus/rib_arb_tb.v'],LOGS/'compile_unit.log')
        output = command([vvp,unit],LOGS/'unit.log')
        if 'TEST_PASS RIB' not in output: raise RuntimeError('No unit PASS marker')
        print(output.strip(),flush=True)
        results.append({'name':'rib_unit','status':'PASS','cases':1003})
    if args.suite in ('isa','data','coremark','all'):
        fixtures = sorted((ROOT/'references/tinyriscv/tests/isa/generated').glob('*.bin')) if args.suite in ('isa','all') else []
        fixtures = [p for p in fixtures if p.name.startswith(('rv32ui-','rv32um-'))]
        if args.suite in ('isa','all') and not fixtures: raise RuntimeError('No ISA fixtures found')
        if args.suite in ('coremark','all'):
            fixtures.append(coremark_binary(args.gcc))
        if args.suite in ('data','all'):
            fixtures.append(ram2_binary(args.gcc))
        programs = {mode:compile_soc(iv,mode) for mode in (0,1)}
        for binary in fixtures:
            hexfile = BUILD/(binary.stem+'.hex')
            image(binary,hexfile)
            is_coremark = binary.name=='coremark_smoke.bin'
            final_crc = None
            for mode in (0,1):
                extra = ['+finish_pc='+(BUILD/'coremark_finish_pc.txt').read_text('ascii')] if is_coremark else []
                output = command([vvp,programs[mode],f'+image={hexfile}',
                                  '+limit='+('3000000' if is_coremark else '250000'),
                                  f'+coremark={int(is_coremark)}',*extra],LOGS/f'{binary.stem}_{mode}.log',
                                 timeout=600 if is_coremark else 120)
                if 'TEST_PASS' not in output: raise RuntimeError(f'No PASS: {binary.name} mode={mode}')
                if is_coremark:
                    for label,value in [('seedcrc','e9f5'),('crclist','e714'),('crcmatrix','1fd7'),('crcstate','8e3a')]:
                        if not re.search(label+r'\s*:\s*0x'+value,output):
                            raise RuntimeError(f'CoreMark {label} mismatch mode={mode}')
                    current_crc = re.search(r'crcfinal\s*:\s*0x([0-9a-fA-F]+)',output)
                    if not current_crc: raise RuntimeError('Missing CoreMark final CRC')
                    if final_crc is not None and current_crc[1] != final_crc:
                        raise RuntimeError('CoreMark final CRC differs between modes')
                    final_crc = current_crc[1]
                cycles = int(re.search(r'TEST_PASS cycles=(\d+)', output)[1])
                item = {'name':binary.stem,'mode':mode,'cycles':cycles,'status':'PASS'}
                grants = re.search(r'parallel_grants=(\d+)',output)
                if grants:
                    item['parallel_grants'] = int(grants[1])
                if binary.name=='ram2_parallel.bin' and mode==1 and not item.get('parallel_grants'):
                    raise RuntimeError('No simultaneous fetch/data requests observed')
                if is_coremark:
                    item['benchmark_cycles'] = int(re.search(r'Benchmark cycles64\s*:\s*(\d+)',output)[1])
                results.append(item)
                print(item,flush=True)
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    report = REPORT.with_name('bus_regression_'+args.suite+'.json')
    report.write_text(json.dumps({'suite':args.suite,'scope':'Functional synchronous RAM models; no FPGA timing verification',
                                  'results':results},indent=2)+'\n',encoding='utf-8')
    print(f'PASS: {len(results)} runs; report: {report}',flush=True)

if __name__=='__main__':
    try:
        main()
    except (RuntimeError,subprocess.TimeoutExpired) as exc:
        print(f'FAIL: {exc}',file=sys.stderr)
        sys.exit(1)
