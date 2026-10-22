"""Freeze the timing cleanup and pairing evidence, rejecting changed inputs."""
from pathlib import Path
from datetime import datetime
import gzip,hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/timing_pair'
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
    assert read(ROOT/'docs/accepted_baseline.json')==read(OUT/'before/accepted_baseline.json')
    old=read(OUT/'before/validation/coremark_performance_10_verilator_stage_final_result.json')
    perf=read(ROOT/'simulation/results/coremark_performance_10_verilator_cleanup1/result.json')
    valid=read(ROOT/'simulation/results/coremark_validation_1_verilator_cleanup1/result.json')
    for result in (perf,valid):
        assert result['status']=='PASS' and result['metrics']['CRC validation']=='PASS'
        for name,digest in result['input_sha256'].items():assert sha(ROOT/name)==digest,name
    assert old['metrics']==perf['metrics'],'Cleanup changed measured CPU behavior'
    assert old['predictor']==perf['predictor'] and old['multiply']==perf['multiply']
    assert old['image_sha256']==perf['image_sha256']==sha(ROOT/'sw/build/boot.hex')
    for suite in ('stage_opt','multiply','prediction','ex_equiv','fetch_equiv','pair_model'):
        folder=ROOT/'simulation/results'/suite;result=read(folder/'result.json');assert result['status']=='PASS',suite
        for key in ('source_sha256','input_sha256','rtl_sha256'):
            for name,digest in result.get(key,{}).items():assert sha(ROOT/name)==digest,(suite,name)
        for p in folder.iterdir():
            if suite=='stage_opt' and p.name!='result.json' and not p.name.startswith('memory_'):continue
            if p.suffix in ('.json','.log'):shutil.copy2(p,OUT/'validation'/f'{suite}_{p.name}')
    for case in ('coremark_performance_10_verilator_cleanup1','coremark_validation_1_verilator_cleanup1'):
        for name in ('result.json','uart.txt','simulation.log'):
            shutil.copy2(ROOT/'simulation/results'/case/name,OUT/'validation'/f'{case}_{name}')
    folder=ROOT/'simulation/results/pair_cleanup1'
    pair=read(folder/'result.json');collection=read(folder/'collection.json')
    assert pair['status']==collection['status']=='PASS'
    for name,digest in collection['input_sha256'].items():assert sha(ROOT/name)==digest,name
    assert sha(folder/'retirements.txt.gz')==pair['trace_gzip_sha256']
    h=hashlib.sha256()
    with gzip.open(folder/'retirements.txt.gz','rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    assert h.hexdigest()==collection['trace_sha256']
    assert pair['retired']==int(perf['metrics']['Retired instructions']) and pair['baseline_cycles']==int(perf['metrics']['Stats window cycles'])
    assert pair['retired_bad_predictions']==perf['predictor']['next_pc_wrong']
    for name in ('result.json','collection.json','retirements.txt.gz','simulation.log','uart.txt','soc_tb_pair.v'):
        shutil.copy2(folder/name,OUT/'validation'/f'pair_{name}')
    save(OUT/'pairing.json',pair)
    shutil.copy2(ROOT/'hardware/pds/cleanup1_build.log',OUT/'validation/pds_build.log')
    shutil.copy2(ROOT/'hardware/pds/new_core.tcl',OUT/'validation/new_core.tcl')
    timing=(OUT/'validation/timing.rtr').read_text(errors='replace');paths=[]
    for b in timing.split('Startpoint  : ')[1:]:
        ep=re.search(r'Endpoint\s+: ([^\n]+)',b);kind=re.search(r'Path Type\s+: ([^\n]+)',b)
        slack=re.search(r'Slack \((?:MET|VIOLATED)\)\s+(-?\d+\.\d+)',b)
        levels=re.search(r'Logic Levels: (\d+)',b);delay=re.search(r'Logic: ([\d.]+)ns.*?Route: ([\d.]+)ns',b)
        if ep and kind and slack:paths.append(dict(start=b.splitlines()[0],end=ep[1],type=kind[1],slack_ns=float(slack[1]),
            levels=int(levels[1]) if levels else None,logic_ns=float(delay[1]) if delay else None,
            route_ns=float(delay[2]) if delay else None))
    save(OUT/'paths.json',paths)
    changed=sorted(k for k,v in after['source_sha256'].items() if before['source_sha256'].get(k)!=v)
    assert changed==['hardware/pds/source/core/nc_memory.v'],changed
    f0=before['pds']['estimated_fmax_mhz'];f1=after['pds']['estimated_fmax_mhz']
    result=dict(status='IMPLEMENTED_AND_VERIFIED',user_accepted=False,date=datetime.now().astimezone().isoformat(),
        before=before['pds'],after=after['pds'],changes=dict(estimated_fmax_percent=(f1/f0-1)*100,
            resources={k:after['pds']['resources'][k]-v for k,v in before['pds']['resources'].items()}),
        coremark_metrics_unchanged=True,coremark=perf['metrics'],predictor_unchanged=True,multiply_unchanged=True,
        image_sha256=perf['image_sha256'],source_sha256=after['source_sha256'],changed_sources=changed,
        pairing='docs/timing_pair/pairing.json',
        limits=['Same approximately 75 MHz PLL and same load latency; Fmax is a PDS estimate.',
            'No extra data pipeline stage, RAM-to-EX bypass, or new cross-stage control chain.',
            'Pairing is a retired-trace structural model; dual fetch/RF/execute/retirement not implemented.',
            'No bitstream or board run.'])
    save(OUT/'comparison.json',result)
    print(json.dumps(dict(status='PASS',changes=result['changes'],pair_count=pair['policies']['full0_alu1']['pairs']),indent=2))
if __name__=='__main__':main()
