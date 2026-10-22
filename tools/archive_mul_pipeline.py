"""Freeze the verified multiply candidate and compare with accepted BTB64."""
from pathlib import Path
from datetime import datetime
import hashlib,json,re,shutil

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/mul_pipeline'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,data):path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def main():
    before=read(OUT/'before/validation/baseline.json')
    after=read(OUT/'validation/baseline.json')
    accepted=read(ROOT/'docs/accepted_baseline.json')
    assert accepted['status']=='ACCEPTED' and accepted['estimated_fmax_mhz']==85.616
    assert accepted['source_sha256']==before['source_sha256']
    for name,sha in after['source_sha256'].items():
        assert digest(ROOT/name)==sha,name
        if name.startswith('hardware/pds/source/'):
            dest=OUT/'source'/Path(name).relative_to('hardware/pds/source')
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
    changed=sorted(k for k,v in after['source_sha256'].items() if before['source_sha256'].get(k)!=v)
    removed=sorted(set(before['source_sha256'])-set(after['source_sha256']))
    assert all(k.startswith('hardware/pds/source/core/') for k in changed+removed)
    assert digest(ROOT/'hardware/pds/source/core/nc_btb.v')==accepted['source_sha256']['hardware/pds/source/core/nc_btb.v']
    old=read(OUT/'before/validation/coremark_performance_10_verilator_btb64_tag_result.json')
    final=read(ROOT/'simulation/results/coremark_performance_10_verilator_mul_final/result.json')
    valid=read(ROOT/'simulation/results/coremark_validation_1_verilator_mul_final/result.json')
    for result in (final,valid):
        assert result['status']=='PASS' and result['metrics']['CRC validation']=='PASS'
        for name,sha in result['input_sha256'].items():assert digest(ROOT/name)==sha,name
    assert final['image_sha256']==old['image_sha256']==digest(ROOT/'sw/build/boot.hex')
    assert final['predictor']==old['predictor']
    for key in ('Retired instructions','Retired loads','Retired stores','BJP instructions','seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal'):
        assert old['metrics'][key]==final['metrics'][key],key
    for suite in ('multiply','prediction','ex_equiv','fetch_equiv'):
        folder=ROOT/'simulation/results'/suite
        result=read(folder/'result.json')
        assert result['status']=='PASS',suite
        for key in ('source_sha256','rtl_sha256','input_sha256'):
            for name,sha in result.get(key,{}).items():assert digest(ROOT/name)==sha,(suite,name)
        for src in folder.iterdir():
            if src.suffix in ('.json','.log'):
                shutil.copy2(src,OUT/'validation'/f'{suite}_{src.name}')
    for case in ('coremark_performance_10_verilator_mul_final','coremark_validation_1_verilator_mul_final'):
        for name in ('result.json','uart.txt','simulation.log'):
            shutil.copy2(ROOT/'simulation/results'/case/name,OUT/'validation'/f'{case}_{name}')
    shutil.copy2(ROOT/'hardware/pds/mul_final_build.log',OUT/'validation/pds_build.log')
    shutil.copy2(ROOT/'hardware/pds/new_core.tcl',OUT/'validation/new_core.tcl')
    timing=(OUT/'validation/timing.rtr').read_text(errors='replace')
    paths=[]
    for block in timing.split('Startpoint  : ')[1:]:
        endpoint=re.search(r'Endpoint\s+: ([^\n]+)',block)
        kind=re.search(r'Path Type\s+: ([^\n]+)',block)
        slack=re.search(r'Slack \((?:MET|VIOLATED)\)\s+(-?\d+\.\d+)',block)
        levels=re.search(r'Logic Levels: (\d+)',block)
        delay=re.search(r'Logic: ([\d.]+)ns.*?Route: ([\d.]+)ns',block)
        if not (endpoint and kind and slack):continue
        paths.append(dict(start=block.splitlines()[0],end=endpoint[1],type=kind[1],slack_ns=float(slack[1]),
            levels=int(levels[1]) if levels else None,logic_ns=float(delay[1]) if delay else None,
            route_ns=float(delay[2]) if delay else None))
    save(OUT/'paths.json',paths)
    def metrics(r):
        m=r['metrics'];cycles=int(m['Stats window cycles']);retired=int(m['Retired instructions'])
        return dict(cycles=cycles,benchmark_cycles=int(m['Benchmark cycles64']),retired=retired,
            ipc=retired/cycles,cpi=cycles/retired,diagnostic_coremark_per_mhz=float(m['CoreMark/MHz']),
            operand_wait=int(m['EX operand wait'].split()[0]),id_blocked=int(m['ID blocked cycles'].split()[0]),
            if_empty=int(m['IF queue empty'].split()[0]),mem_occupied=int(m['MEM occupied cycles'].split()[0]),
            muldiv_ex_stall=int(m['Mul/div stall cycles'].split()[0]))
    b,a=metrics(old),metrics(final)
    scaled=(b['cycles']/a['cycles'])*(after['pds']['estimated_fmax_mhz']/before['pds']['estimated_fmax_mhz'])-1
    result=dict(status='IMPLEMENTED_AND_VERIFIED',user_accepted=False,
        date=datetime.now().astimezone().isoformat(),accepted_baseline='docs/accepted_baseline.json',
        note='BTB64 remains accepted. Multiply candidate has not been marked accepted by the user.',
        before=dict(coremark=b,pds=before['pds']),after=dict(coremark=a,pds=after['pds'],multiply=final['multiply']),
        changes=dict(cycle_reduction_percent=(1-a['cycles']/b['cycles'])*100,
            same_clock_throughput_percent=(b['cycles']/a['cycles']-1)*100,
            estimated_fmax_percent=(after['pds']['estimated_fmax_mhz']/before['pds']['estimated_fmax_mhz']-1)*100,
            hypothetical_separate_fmax_throughput_percent=scaled*100,
            resource_delta={k:after['pds']['resources'][k]-v for k,v in before['pds']['resources'].items()}),
        predictor_unchanged=True,image_sha256=final['image_sha256'],changed_sources=changed,removed_sources=removed,
        source_sha256=after['source_sha256'],
        experiments=[dict(name='serial_select',fmax_mhz=80.913,status='superseded; uniform three-cycle result'),
            dict(name='parallel_select',fmax_mhz=80.998,status='rejected; hold violations and extra LUT'),
            dict(name='early_low_before_empty_fix',fmax_mhz=85.339,status='superseded; false MEM occupied count on stale empty MUL payload'),
            dict(name='final',fmax_mhz=83.879,status='all setup/hold and functional checks pass')],
        limits=['Same 75 MHz PLL; no bitstream or board measurement.',
            'Fmax is one implementation estimate, not a demonstrated maximum-frequency run.',
            'Short CoreMark diagnostic; not a certified score.',
            'No EX early memory access or raw RAM forward path.',
            'One multiply broadcast port; simultaneous high/low results both buffered, low broadcasts first.'])
    save(OUT/'comparison.json',result)
    print(json.dumps(dict(status='PASS',changes=result['changes'],changed=changed,removed=removed,archived_paths=len(paths)),indent=2))

if __name__=='__main__':main()
