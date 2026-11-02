"""Build the imported CoreMark with the new SoC ABI; no old binary patching."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, re
ROOT = Path(__file__).resolve().parents[1]
PROFILES = {'baseline': [], 'o3': ['-O3'], 'no_unroll': ['-fno-unroll-loops'],
            'schedule': ['-fschedule-insns', '-fschedule-insns2'],
            'o3_inline80': ['-O3', '--param=max-inline-insns-auto=80'],
            'o3_inline80_tune7': ['-O3', '--param=max-inline-insns-auto=80', '-mtune=sifive-7-series'],
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
    p.add_argument('--extra-cflag',action='append',default=[],help='Append an explicit compiler option; repeat as --extra-cflag=VALUE')
    p.add_argument('--module-cflag',action='append',default=[],help='Override one source module: --module-cflag=core_list_join.c:-mbranch-cost=1; repeat for additional flags')
    p.add_argument('--stack-offset',type=int,default=0,help='Optional16-byte-aligned stack coloring offset; keep original linker script unchanged')
    p.add_argument('--source-date-epoch', type=int, help='Reproducible build timestamp')
    a=p.parse_args()
    if a.iterations<1:p.error('iterations must be positive; use an explicit count for reproducibility')
    if a.cpu_hz<=0:p.error('cpu-hz must be positive and match the hardware PLL')
    if a.stack_offset<0 or a.stack_offset>4096 or a.stack_offset%16:p.error('stack-offset must be a multiple of16 in0..4096')
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
    flags += PROFILES[a.profile]+a.extra_cflag
    linker=ROOT/'sw/link.lds'
    layout={}
    if a.stack_offset:
        original_linker=linker;old='__stack_top = ORIGIN(DATA) + LENGTH(DATA);'
        text=original_linker.read_text();assert text.count(old)==1
        linker=out/'coremark_stack.ld';linker.write_text(text.replace(old,'__stack_top = ORIGIN(DATA) + LENGTH(DATA) - __stack_offset;'))
        flags.append(f'-Wl,--defsym=__stack_offset=0x{a.stack_offset:08x}')
        layout=dict(stack_offset=a.stack_offset,base_linker_script_sha256=hashlib.sha256(original_linker.read_bytes()).hexdigest(),
                    linker_script=str(linker.relative_to(ROOT)),linker_script_sha256=hashlib.sha256(linker.read_bytes()).hexdigest())
    sources=[ROOT/'sw/start.S',*sorted((ROOT/'sw/coremark').glob('*.c')),
             *[ROOT/'sw/lib'/x for x in ('xprintf.c','utils.c','uart.c')]]
    module_flags={}
    for item in a.module_cflag:
        name,sep,flag=item.partition(':')
        if not sep or name not in {s.name for s in sources} or not flag.startswith('-'):
            p.error('module-cflag must name one source basename and a compiler flag')
        module_flags.setdefault(name,[]).append(flag)
    reported_flags=' '.join(flags)+''.join(' ['+s.name+': '+' '.join(module_flags[s.name])+']' for s in sources if s.name in module_flags)
    cmd=[str(gcc),*flags,f'-DITERATIONS={a.iterations}',f'-DCPU_FREQ_HZ={a.cpu_hz}',f'-DCPU_FREQ_MHZ={a.cpu_hz//1000000}',f'-DPERFORMANCE_RUN={int(not a.validation)}',
         f'-DVALIDATION_RUN={int(a.validation)}','-DTOTAL_DATA_SIZE=2000',
         '-DFLAGS_STR="'+reported_flags+'"','-nostdlib','-Wl,--gc-sections','-Wl,--build-id=none',
         '-Wl,-Map='+str(out/'coremark.map'),'-T',str(linker),
         *map(str,sources),'-lc','-lgcc','-o',str(out/'coremark.elf')]
    compile_commands=[]
    source_args={str(s) for s in sources}
    for source in sources:
        if source.name not in module_flags:continue
        obj=out/(source.stem+'.o');part=[];skip=False
        for value in cmd:
            if skip:skip=False;continue
            if value in ('-o','-T'):skip=True;continue
            if value in source_args or value in ('-lc','-lgcc','-nostdlib') or value.startswith('-Wl,'):continue
            # Earlier explicit objects belong only to the final link.
            if value in [str(out/(s.stem+'.o')) for s in sources]:continue
            part.append(value)
        part+=module_flags[source.name]+['-c',str(source),'-o',str(obj)]
        subprocess.run(part,check=True);compile_commands.append(part)
        cmd[cmd.index(str(source))]=str(obj)
    subprocess.run(cmd,check=True)
    if a.stack_offset:
        symbols=subprocess.run([str(gcc.with_name(gcc.name.replace('gcc','readelf'))),'-s',str(out/'coremark.elf')],capture_output=True,text=True,check=True).stdout
        (out/'symbols.txt').write_text(symbols)
        values={name:int(value,16) for value,name in re.findall(r'^\s*\d+:\s*([0-9a-f]+)\s+.*\s(__stack_top|__bss_end)\s*$',symbols,re.M)}
        assert values['__stack_top']==0x10008000-a.stack_offset and values['__stack_top']%16==0
        assert values['__bss_end']+2048<=values['__stack_top'],'Actual ELF must retain at least2KB stack aboveBSS'
        layout.update(stack_top=values['__stack_top'],bss_end=values['__bss_end'],builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    subprocess.run([str(gcc.with_name(gcc.name.replace('gcc','objcopy'))),'-O','binary',
                    str(out/'coremark.elf'),str(out/'coremark.bin')],check=True)
    data=(out/'coremark.bin').read_bytes()
    assert 0<len(data)<=65536
    padded=data+bytes(65536-len(data))
    (out/'coremark.hex').write_text(''.join(f'{int.from_bytes(padded[i:i+4],"little"):08x}\n' for i in range(0,65536,4)))
    with (out/'coremark.dump').open('w') as f:
        subprocess.run([str(gcc.with_name(gcc.name.replace('gcc','objdump'))),'-d',str(out/'coremark.elf')],stdout=f,check=True)
    manifest={'iterations':a.iterations,'validation':a.validation,'cpu_hz':a.cpu_hz,'command':cmd,
              'optimization_profile':a.profile,'extra_cflags':a.extra_cflag,'module_cflags':module_flags,'compile_commands':compile_commands,'source_date_epoch':os.environ.get('SOURCE_DATE_EPOCH'),
              'image_bytes':len(data),'binary_sha256':hashlib.sha256(data).hexdigest(),
              'sources':{str(s.relative_to(ROOT)):hashlib.sha256(s.read_bytes()).hexdigest() for s in sources},
              'headers':{str(s.relative_to(ROOT)):hashlib.sha256(s.read_bytes()).hexdigest() for s in sorted((ROOT/'sw').rglob('*.h'))},
              'hex_sha256':hashlib.sha256((out/'coremark.hex').read_bytes()).hexdigest()}
    manifest.update(layout)
    (out/'build.json').write_text(json.dumps(manifest,indent=2))
    if a.install:shutil.copyfile(out/'coremark.hex',ROOT/'sw/build/boot.hex')
    print('COREMARK_IMAGE',out/'coremark.hex',f'({len(data)} bytes)')
if __name__=='__main__':main()
