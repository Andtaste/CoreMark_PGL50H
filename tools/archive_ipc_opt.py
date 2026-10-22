"""Freeze IPC experiments, verify every measured source against its snapshot."""
from pathlib import Path
from datetime import datetime
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/ipc_opt'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
def verify_hashes(result,overrides=None):
    overrides=overrides or {}
    for key in ('input_sha256','source_sha256','rtl_sha256'):
        for name,digest in result.get(key,{}).items():
            assert sha(overrides.get(name.replace('\\','/'),ROOT/name))==digest,name
def main():
    before=read(OUT/'before/validation/baseline.json');after=read(OUT/'validation/baseline.json')
    accepted=read(ROOT/'docs/accepted_baseline.json')
    assert accepted==read(OUT/'before/accepted_baseline.json')
    assert accepted['source_sha256']==before['source_sha256']
    for name,digest in after['source_sha256'].items():
        assert sha(ROOT/name)==digest,name
        if name.startswith('hardware/pds/source/'):
            copy(ROOT/name,OUT/'source'/Path(name).relative_to('hardware/pds/source'))
    changed=sorted(k for k,v in after['source_sha256'].items() if before['source_sha256'].get(k)!=v)
    assert changed==['hardware/pds/source/core/nc_btb.v','hardware/pds/source/core/nc_memory.v'],changed
    old_btb=OUT/'before/source/core/nc_btb.v';old_mem=OUT/'before/source/core/nc_memory.v'
    cases={};fixed=('Retired instructions','Retired loads','Retired stores','BJP instructions','CRC validation','Compiler flags','CoreMark Size','seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal')
    for tag in ('cleanup1','ipc_lh1','ipc_mem','ipc_combo'):
        folder=ROOT/f'simulation/results/coremark_performance_10_verilator_{tag}';x=read(folder/'result.json')
        overrides={}
        if tag in ('cleanup1','ipc_mem'):overrides['hardware/pds/source/core/nc_btb.v']=old_btb
        if tag in ('cleanup1','ipc_lh1'):overrides['hardware/pds/source/core/nc_memory.v']=old_mem
        assert x['status']=='PASS';verify_hashes(x,overrides)
        assert x['image_sha256']==sha(ROOT/'sw/build/boot.hex')
        assert x['metrics']['CRC validation']=='PASS'
        for k in fixed:assert x['metrics'][k]==cases.get('cleanup1',x)['metrics'][k],(tag,k)
        for n in ('result.json','uart.txt','simulation.log'):copy(folder/n,OUT/'validation'/f'{folder.name}_{n}')
        cases[tag]=x
    val_folder=ROOT/'simulation/results/coremark_validation_1_verilator_ipc_final';val=read(val_folder/'result.json')
    assert val['status']=='PASS';verify_hashes(val)
    for n in ('result.json','uart.txt','simulation.log'):copy(val_folder/n,OUT/'validation'/f'{val_folder.name}_{n}')
    for suite in ('stage_opt','prediction','multiply','fetch_equiv','ex_equiv','pair_model'):
        folder=ROOT/'simulation/results'/suite;x=read(folder/'result.json');assert x['status']=='PASS',suite;verify_hashes(x)
        for p in folder.iterdir():
            if p.suffix in ('.json','.log'):copy(p,OUT/'validation'/f'{suite}_{p.name}')
    assert read(ROOT/'simulation/results/regression.json')==read(OUT/'validation/regression.json')
    assert read(ROOT/'simulation/results/isa.json')==read(OUT/'validation/isa.json')
    profiles={}
    for tag in ('accepted','final'):
        folder=ROOT/f'simulation/results/ipc_profile_{tag}';c=read(folder/'collection.json');p=read(folder/'result.json')
        overrides={'hardware/pds/source/core/nc_btb.v':old_btb,'hardware/pds/source/core/nc_memory.v':old_mem} if tag=='accepted' else {}
        verify_hashes(c,overrides);profiles[tag]=dict(collection=c,result=p)
        for n in ('collection.json','result.json','branches.txt.gz','simulation.log','uart.txt','soc_tb_ipc.v'):
            copy(folder/n,OUT/'validation'/f'ipc_profile_{tag}_{n}')
    waits=read(ROOT/'simulation/results/wait_profile_ipc_final/result.json');assert waits['status']=='PASS';verify_hashes(waits)
    for n in ('result.json','simulation.log','soc_tb_profile.v','uart.txt'):
        copy(ROOT/'simulation/results/wait_profile_ipc_final'/n,OUT/'validation'/f'wait_{n}')
    for p in ('archive_ipc_opt.py','profile_ipc.py','profile_waits.py','screen_predictors.py','check_stage_opt.py','check_prediction.py','collect_validation.py','run.ps1'):
        copy(ROOT/'tools'/p,OUT/'tools'/p)
    for p in ('btb_tb.v','memory_turnover_tb.v','memory_overlap_tb.v'):copy(ROOT/'simulation/tb'/p,OUT/'tests'/p)
    for p in ('ipc_final_tests.log','ipc_final_waits.log','ipc_final_validation.log'):copy(ROOT/'simulation/results'/p,OUT/'validation'/p)
    copy(ROOT/'hardware/pds/ipc_combo_build.log',OUT/'validation/pds_build.log')
    copy(ROOT/'hardware/pds/new_core.tcl',OUT/'validation/new_core.tcl')
    paths=[]
    for b in (OUT/'validation/timing.rtr').read_text(errors='replace').split('Startpoint  : ')[1:]:
        ep=re.search(r'Endpoint\s+: ([^\n]+)',b);kind=re.search(r'Path Type\s+: ([^\n]+)',b)
        slack=re.search(r'Slack \((?:MET|VIOLATED)\)\s+(-?\d+\.\d+)',b);levels=re.search(r'Logic Levels: (\d+)',b)
        delay=re.search(r'Logic: ([\d.]+)ns.*?Route: ([\d.]+)ns',b)
        if ep and kind and slack:paths.append(dict(start=b.splitlines()[0],end=ep[1],type=kind[1],slack_ns=float(slack[1]),levels=int(levels[1]) if levels else None,logic_ns=float(delay[1]) if delay else None,route_ns=float(delay[2]) if delay else None))
    save(OUT/'paths.json',paths)
    old=cases['cleanup1'];new=cases['ipc_combo'];c0=int(old['metrics']['Stats window cycles']);c1=int(new['metrics']['Stats window cycles']);inst=int(new['metrics']['Retired instructions'])
    result=dict(status='IMPLEMENTED_AND_VERIFIED',user_accepted=False,date=datetime.now().astimezone().isoformat(),
        accepted_baseline='docs/accepted_baseline.json',changed_sources=changed,source_sha256=after['source_sha256'],
        before=dict(pds=before['pds'],cycles=c0,retired=inst,ipc=inst/c0,coremark_per_mhz=float(old['metrics']['CoreMark/MHz'])),
        after=dict(pds=after['pds'],cycles=c1,retired=inst,ipc=inst/c1,coremark_per_mhz=float(new['metrics']['CoreMark/MHz'])),
        changes=dict(cycles_saved=c0-c1,cycle_reduction_percent=(1-c1/c0)*100,same_clock_speedup_percent=(c0/c1-1)*100,
            estimated_fmax_percent=(after['pds']['estimated_fmax_mhz']/before['pds']['estimated_fmax_mhz']-1)*100,
            combined_estimate_percent=(c0/c1*after['pds']['estimated_fmax_mhz']/before['pds']['estimated_fmax_mhz']-1)*100,
            resources={k:after['pds']['resources'][k]-v for k,v in before['pds']['resources'].items()}),
        ablations={k:dict(cycles=int(x['metrics']['Stats window cycles']),ipc=inst/int(x['metrics']['Stats window cycles']),predictor=x['predictor']) for k,x in cases.items()},
        load_phases={k:x['collection']['load_wait_phase'] for k,x in profiles.items()},
        load_ex_to_request={k:x['collection']['load_ex_to_request'] for k,x in profiles.items()},
        final_waits=waits['counts'],image_sha256=new['image_sha256'],
        limits=['Same fixed image; single issue and one bus transaction remain.',
            'Estimated Fmax only; actual PLL remains approximately 75 MHz. No board run.',
            'Screening models omit speculative lookup/training latency and are not IPC measurements.',
            'Saved prediction hit=0 includes correction commands that bypass BTB lookup; it is not a pure capacity-miss count.',
            'Wait counters overlap. Changes are evaluated by total same-window cycles, not summed wait counts.'])
    save(OUT/'comparison.json',result)
    files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='manifest.json']
    save(OUT/'manifest.json',dict(status='PASS',files_sha256={str(p.relative_to(OUT)):sha(p) for p in sorted(files)}))
    print(json.dumps(dict(status='PASS',changes=result['changes'],after=result['after']),indent=2))
if __name__=='__main__':main()
