"""Multiply arithmetic, buffered completion, in-order overlap and precise squash."""
from pathlib import Path
import sys,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'simulation/scripts/run'))
from regression import find,run,build,differential

def main():
    out=ROOT/'simulation/results/multiply';out.mkdir(parents=True,exist_ok=True)
    iv=find('iverilog',[ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe'])
    vvp=find('vvp',[ROOT.parent/'tmp/iverilog-portable/bin/vvp.exe'])
    gcc=find('riscv-none-elf-gcc',Path('D:/Program Files/riscv').glob('**/riscv-none-elf-gcc.exe'))
    rtl=sorted((ROOT/'hardware/pds/source/core').glob('*.v'))
    run([iv,'-g2012','-s','mul_pipeline_tb','-o',out/'unit.vvp',ROOT/'hardware/pds/source/core/nc_mul_pipeline.v',ROOT/'simulation/tb/mul_pipeline_tb.v'],out/'unit_compile.log')
    result=run([vvp,out/'unit.vvp'],out/'unit.log');assert 'PASS multiply pipeline' in result,result
    results=[{'test':'mul_pipeline_model','status':'PASS','summary':result.strip()}]
    run([iv,'-g2012','-DMUL_PIPE_TEST','-s','core_tb','-o',out/'core.vvp',*rtl,ROOT/'simulation/tb/core_tb.v'],out/'core_compile.log')
    images={n:build(gcc,ROOT/f'simulation/tests/{n}.S',n) for n in ['multiply_overlap','multiply_trap']}
    for name,(image,data) in images.items():
        for seed in (37,613):
            trace=out/f'{name}_{seed}.trace'
            result=run([vvp,out/'core.vvp',f'+image={image}',f'+trace={trace}',f'+seed={seed}'],out/f'{name}_{seed}.log')
            assert 'PASS cycles=' in result,result
            stats={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',result.split('MUL_CORE ')[1])}
            item={'test':f'{name}_{seed}','status':'PASS','stats':stats,'summary':result.strip()}
            if name=='multiply_overlap':
                item['differential_retirements']=differential(data,trace)
                assert stats['accepts']>400 and stats['accepts']==stats['consumes'] and stats['overlap']>0 and stats['mem_overlap']>0,stats
            else:
                causes=[int(x.split()[5],16) for x in trace.read_text().splitlines() if int(x.split()[4])]
                assert causes==[5] and stats['trap_cancels']>0 and stats['accepts']>stats['consumes'],(causes,stats)
            results.append(item)
    # Synchronous SoC RAM supplies consecutive instructions for a burst of
    # independent MULs; random-latency core tests above stress memory stalls.
    socrtl=rtl+sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('perips','sys_bus','top')],[])
    run([iv,'-g2012','-s','soc_tb','-o',out/'soc.vvp',*socrtl,ROOT/'simulation/models/pango_ram_models.v',ROOT/'simulation/tb/soc_tb.v'],out/'soc_compile.log')
    for name,(image,data) in images.items():
        trace=out/f'soc_{name}.trace';result=run([vvp,out/'soc.vvp',f'+image={image}',f'+trace={trace}'],out/f'soc_{name}.log')
        assert 'PASS cycles=' in result,result
        item={'test':f'soc_{name}','status':'PASS','summary':result.strip()}
        if name=='multiply_overlap':item['differential_retirements']=differential(data,trace)
        else:assert [int(x.split()[5],16) for x in trace.read_text().splitlines() if int(x.split()[4])]==[5]
        results.append(item)
    inputs=socrtl+[ROOT/'simulation/tb/core_tb.v',ROOT/'simulation/tb/soc_tb.v',ROOT/'simulation/tb/mul_pipeline_tb.v']+[ROOT/f'simulation/tests/{n}.S' for n in images]
    (out/'result.json').write_text(json.dumps({'status':'PASS','results':results,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}},indent=2))
    for item in results:print(item['test'],item['summary'])
if __name__=='__main__':main()
