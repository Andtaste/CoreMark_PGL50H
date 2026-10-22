"""BTB model + predictor recovery/FENCE.I under random and SoC memory latency."""
from pathlib import Path
import sys,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'simulation/scripts/run'))
from regression import find,run,build,differential

def main():
    out=ROOT/'simulation/results/prediction';out.mkdir(parents=True,exist_ok=True)
    iv=find('iverilog',[ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe'])
    vvp=find('vvp',[ROOT.parent/'tmp/iverilog-portable/bin/vvp.exe'])
    gcc=find('riscv-none-elf-gcc',Path('D:/Program Files/riscv').glob('**/riscv-none-elf-gcc.exe'))
    rtl=sorted((ROOT/'hardware/pds/source/core').glob('*.v'))
    run([iv,'-g2012','-s','btb_tb','-o',out/'btb.vvp',ROOT/'hardware/pds/source/core/nc_btb.v',ROOT/'simulation/tb/btb_tb.v'],out/'btb_compile.log')
    result=run([vvp,out/'btb.vvp'],out/'btb.log');assert 'PASS BTB model updates=20000' in result,result
    image,data=build(gcc,ROOT/'simulation/tests/prediction.S','prediction')
    results=[{'test':'btb_model','status':'PASS','summary':result.strip()}]
    run([iv,'-g2012','-s','core_tb','-o',out/'core.vvp',*rtl,ROOT/'simulation/tb/core_tb.v'],out/'core_compile.log')
    for seed in (37,613):
        trace=out/f'core_{seed}.trace'
        result=run([vvp,out/'core.vvp',f'+image={image}',f'+trace={trace}',f'+seed={seed}'],out/f'core_{seed}.log')
        assert 'PASS cycles=' in result,result
        compared=differential(data,trace)
        results.append({'test':f'prediction_core_{seed}','status':'PASS','retirements':compared,'summary':result.strip()})
    socrtl=rtl+sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('perips','sys_bus','top')],[])
    run([iv,'-g2012','-s','soc_tb','-o',out/'soc.vvp',*socrtl,ROOT/'simulation/models/pango_ram_models.v',ROOT/'simulation/tb/soc_tb.v'],out/'soc_compile.log')
    trace=out/'soc.trace';result=run([vvp,out/'soc.vvp',f'+image={image}',f'+trace={trace}'],out/'soc.log')
    assert 'PASS cycles=' in result,result
    results.append({'test':'prediction_soc','status':'PASS','retirements':differential(data,trace),'summary':result.strip()})
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in socrtl+[ROOT/'simulation/tests/prediction.S',ROOT/'simulation/tb/btb_tb.v']}
    (out/'result.json').write_text(json.dumps({'status':'PASS','results':results,'source_sha256':hashes},indent=2))
    for item in results:print(item['test'],item['summary'])
if __name__=='__main__':main()
