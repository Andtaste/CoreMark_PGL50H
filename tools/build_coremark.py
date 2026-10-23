"""Build the imported CoreMark with the new SoC ABI; no old binary patching."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, re
ROOT = Path(__file__).resolve().parents[1]
PROFILES = {'baseline': [], 'o3': ['-O3'], 'no_unroll': ['-fno-unroll-loops'],
            'schedule': ['-fschedule-insns', '-fschedule-insns2'],
            'o3_inline80': ['-O3', '--param=max-inline-insns-auto=80'],
            'o3_align8': ['-O3', '-falign-functions=8', '-falign-jumps=8', '-falign-loops=8']}
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--iterations',type=int,default=5000)
    p.add_argument('--cpu-hz',type=int,default=82000000)
    p.add_argument('--tag',default='',help='Keep rebuilt diagnostic images separate from historical fixed images')
    p.add_argument('--validation',action='store_true')
    p.add_argument('--install',action='store_true',help='Select as FPGA boot.hex; regenerate Pango RAM afterward')
    p.add_argument('--gcc')
    p.add_argument('--profile', choices=PROFILES, default='baseline')
    p.add_argument('--source-date-epoch', type=int, help='Reproducible build timestamp')
    a=p.parse_args()
    if a.iterations<1:p.error('iterations must be positive; use an explicit count for reproducibility')
    if a.cpu_hz<=0:p.error('cpu-hz must be positive and match the hardware PLL')
    if a.source_date_epoch is not None:
        if a.source_date_epoch<0:p.error('source-date-epoch must be nonnegative')
        os.environ['SOURCE_DATE_EPOCH']=str(a.source_date_epoch)
    if a.tag and not re.fullmatch(r'[A-Za-z0-9_-]+',a.tag):p.error('invalid output tag')
    gcc=Path(a.gcc or shutil.which('riscv-none-elf-gcc') or next(Path('D:/Program Files/riscv').glob('**/riscv-none-elf-gcc.exe')))
    name=f'coremark_{"validation" if a.validation else "performance"}_{a.iterations}'
    if a.tag:name+='_'+a.tag
    out=ROOT/'sw/build'/name;out.mkdir(parents=True,exist_ok=True)
    # Original project's optimization choices, plus new startup's no-GP/no-relax ABI.
    flags=['-O2','-fno-common','-funroll-loops','-finline-functions','--param=max-inline-insns-auto=20',
           '-falign-functions=4','-falign-jumps=4','-falign-loops=4','-march=rv32im_zicsr','-mabi=ilp32',
           '-mcmodel=medlow','-ffunction-sections','-fdata-sections','-fno-builtin-printf',
           '-fno-builtin-malloc','-msmall-data-limit=0','-mno-relax']
    flags += PROFILES[a.profile]
    sources=[ROOT/'sw/start.S',*sorted((ROOT/'sw/coremark').glob('*.c')),
             *[ROOT/'sw/lib'/x for x in ('xprintf.c','utils.c','uart.c')]]
    cmd=[str(gcc),*flags,f'-DITERATIONS={a.iterations}',f'-DCPU_FREQ_HZ={a.cpu_hz}',f'-DCPU_FREQ_MHZ={a.cpu_hz//1000000}',f'-DPERFORMANCE_RUN={int(not a.validation)}',
         f'-DVALIDATION_RUN={int(a.validation)}','-DTOTAL_DATA_SIZE=2000',
         '-DFLAGS_STR="'+' '.join(flags)+'"','-nostdlib','-Wl,--gc-sections','-Wl,--build-id=none',
         '-Wl,-Map='+str(out/'coremark.map'),'-T',str(ROOT/'sw/link.lds'),
         *map(str,sources),'-lc','-lgcc','-o',str(out/'coremark.elf')]
    subprocess.run(cmd,check=True)
    subprocess.run([str(gcc.with_name(gcc.name.replace('gcc','objcopy'))),'-O','binary',
                    str(out/'coremark.elf'),str(out/'coremark.bin')],check=True)
    data=(out/'coremark.bin').read_bytes()
    assert 0<len(data)<=65536
    padded=data+bytes(65536-len(data))
    (out/'coremark.hex').write_text(''.join(f'{int.from_bytes(padded[i:i+4],"little"):08x}\n' for i in range(0,65536,4)))
    with (out/'coremark.dump').open('w') as f:
        subprocess.run([str(gcc.with_name(gcc.name.replace('gcc','objdump'))),'-d',str(out/'coremark.elf')],stdout=f,check=True)
    manifest={'iterations':a.iterations,'validation':a.validation,'cpu_hz':a.cpu_hz,'command':cmd,
              'optimization_profile':a.profile,'source_date_epoch':os.environ.get('SOURCE_DATE_EPOCH'),
              'image_bytes':len(data),'binary_sha256':hashlib.sha256(data).hexdigest(),
              'sources':{str(s.relative_to(ROOT)):hashlib.sha256(s.read_bytes()).hexdigest() for s in sources},
              'headers':{str(s.relative_to(ROOT)):hashlib.sha256(s.read_bytes()).hexdigest() for s in sorted((ROOT/'sw').rglob('*.h'))},
              'hex_sha256':hashlib.sha256((out/'coremark.hex').read_bytes()).hexdigest()}
    (out/'build.json').write_text(json.dumps(manifest,indent=2))
    if a.install:shutil.copyfile(out/'coremark.hex',ROOT/'sw/build/boot.hex')
    print('COREMARK_IMAGE',out/'coremark.hex',f'({len(data)} bytes)')
if __name__=='__main__':main()
