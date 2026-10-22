"""Archive the final stage-optimization implementation and verify all hashes."""
from pathlib import Path
from datetime import datetime
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/stage_opt'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def main():
    before=read(OUT/'before/validation/baseline.json');after=read(OUT/'validation/baseline.json')
    for name,digest in after['source_sha256'].items():
        assert sha(ROOT/name)==digest,name
        if name.startswith('hardware/pds/source/'):
            dest=OUT/'source'/Path(name).relative_to('hardware/pds/source')
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
    accepted=read(ROOT/'docs/accepted_baseline.json')
    assert accepted==read(OUT/'before/accepted_baseline.json'),'Accepted BTB record changed'
    old=read(OUT/'before/validation/coremark_performance_10_verilator_mul_final_result.json')
    perf=read(ROOT/'simulation/results/coremark_performance_10_verilator_stage_final/result.json')
    valid=read(ROOT/'simulation/results/coremark_validation_1_verilator_stage_final/result.json')
    for result in (perf,valid):
        assert result['status']=='PASS' and result['metrics']['CRC validation']=='PASS'
        for name,digest in result['input_sha256'].items():assert sha(ROOT/name)==digest,name
    assert old['image_sha256']==perf['image_sha256']==sha(ROOT/'sw/build/boot.hex')
    assert old['predictor']==perf['predictor']
    for key in ('Retired instructions','Retired loads','Retired stores','BJP instructions','seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal'):
        assert old['metrics'][key]==perf['metrics'][key],key
    for suite in ('stage_opt','multiply','prediction','ex_equiv','fetch_equiv','wait_profile_stage_final'):
        folder=ROOT/'simulation/results'/suite;result=read(folder/'result.json')
        assert result['status']=='PASS',suite
        for key in ('source_sha256','rtl_sha256','input_sha256'):
            for name,digest in result.get(key,{}).items():assert sha(ROOT/name)==digest,(suite,name)
        for p in folder.iterdir():
            if suite=='stage_opt' and p.name!='result.json' and not p.name.startswith('memory_'):continue
            if p.suffix in ('.log','.json','.txt'):
                shutil.copy2(p,OUT/'validation'/f'{suite}_{p.name}')
    for case in ('coremark_performance_10_verilator_stage_final','coremark_validation_1_verilator_stage_final'):
        for name in ('result.json','uart.txt','simulation.log'):
            shutil.copy2(ROOT/'simulation/results'/case/name,OUT/'validation'/f'{case}_{name}')
    shutil.copy2(ROOT/'hardware/pds/stage_final_build.log',OUT/'validation/pds_build.log')
    shutil.copy2(ROOT/'hardware/pds/new_core.tcl',OUT/'validation/new_core.tcl')
    timing=(OUT/'validation/timing.rtr').read_text(errors='replace');paths=[]
    for b in timing.split('Startpoint  : ')[1:]:
        ep=re.search(r'Endpoint\s+: ([^\n]+)',b);kind=re.search(r'Path Type\s+: ([^\n]+)',b)
        slack=re.search(r'Slack \((?:MET|VIOLATED)\)\s+(-?\d+\.\d+)',b)
        level=re.search(r'Logic Levels: (\d+)',b);delay=re.search(r'Logic: ([\d.]+)ns.*?Route: ([\d.]+)ns',b)
        if ep and kind and slack:
            paths.append(dict(start=b.splitlines()[0],end=ep[1],type=kind[1],slack_ns=float(slack[1]),
                levels=int(level[1]) if level else None,logic_ns=float(delay[1]) if delay else None,
                route_ns=float(delay[2]) if delay else None))
    save(OUT/'paths.json',paths)
    def metrics(result):
        m=result['metrics'];c=int(m['Stats window cycles']);n=int(m['Retired instructions'])
        return dict(cycles=c,benchmark_cycles=int(m['Benchmark cycles64']),retired=n,ipc=n/c,cpi=c/n,
            diagnostic_coremark_per_mhz=float(m['CoreMark/MHz']),
            waits={k:int(m[k].split()[0]) for k in ('EX operand wait','ID blocked cycles','IF queue empty','MEM occupied cycles','Mul/div stall cycles')})
    b,a=metrics(old),metrics(perf);f0=before['pds']['estimated_fmax_mhz'];f1=after['pds']['estimated_fmax_mhz']
    changed=sorted(k for k,v in after['source_sha256'].items() if before['source_sha256'].get(k)!=v)
    assert all(k.startswith('hardware/pds/source/core/') for k in changed)
    history=[]
    for folder in ('stage1','stage2b','stage3','stage4','stage5_id3','stage6_ff'):
        path=OUT/folder/'validation/baseline.json'
        if path.exists():
            r=read(path);cm=read(path.parent/'coremark_result.json')
            history.append(dict(name=folder,pds=r['pds'],coremark=metrics(cm)))
    result=dict(status='IMPLEMENTED_AND_VERIFIED',user_accepted=False,date=datetime.now().astimezone().isoformat(),
        accepted_baseline='docs/accepted_baseline.json',before=dict(pds=before['pds'],coremark=b),
        after=dict(pds=after['pds'],coremark=a,multiply=perf['multiply']),
        changes=dict(cycle_reduction_percent=(1-a['cycles']/b['cycles'])*100,
            same_clock_throughput_percent=(b['cycles']/a['cycles']-1)*100,
            estimated_fmax_percent=(f1/f0-1)*100,
            hypothetical_separate_fmax_throughput_percent=(b['cycles']/a['cycles']*f1/f0-1)*100,
            resources={k:after['pds']['resources'][k]-v for k,v in before['pds']['resources'].items()}),
        changed_sources=changed,source_sha256=after['source_sha256'],image_sha256=perf['image_sha256'],
        predictor_unchanged=True,history=history,
        notes=['Same PLL, image, compiler flags, BTB and IF FIFO8.',
            'No raw RAM to EX bypass, EX early memory request or backward combinational ready cascade.',
            'Successful registered response metadata authorizes MEM turnover; failed response suppresses the successor before WB kill.',
            'Wait counters overlap and are not additive cycle savings.',
            'Estimated Fmax and short diagnostic CoreMark; no bitstream or board run.'])
    save(OUT/'comparison.json',result)
    print(json.dumps(dict(status='PASS',changes=result['changes'],changed_sources=changed),indent=2))
if __name__=='__main__':main()
