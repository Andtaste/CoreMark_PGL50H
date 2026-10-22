"""Archive fixed-cycle EX/ID timing candidates without mixing STA or sources."""
from pathlib import Path
from datetime import datetime
import argparse,hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/ex_id_finish'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def verify(x,override=None):
    override=override or {}
    for key in ('source_sha256','input_sha256','rtl_sha256'):
        for n,h in x.get(key,{}).items():assert sha(override.get(n.replace('\\','/'),ROOT/n))==h,n
def paths(text):
    result=[]
    for b in text.split('Startpoint  : ')[1:]:
        ep=re.search(r'Endpoint\s+: ([^\n]+)',b);kind=re.search(r'Path Type\s+: ([^\n]+)',b)
        slack=re.search(r'Slack \((?:MET|VIOLATED)\)\s+(-?\d+\.\d+)',b);levels=re.search(r'Logic Levels: (\d+)',b)
        delay=re.search(r'Logic:\s*([\d.\s]+)ns.*?Route:\s*([\d.\s]+)ns',b,re.S)
        if ep and kind and slack:result.append(dict(start=b.splitlines()[0],end=ep[1],type=kind[1],slack_ns=float(slack[1]),
            levels=int(levels[1]) if levels else None,logic_ns=float(re.sub(r'\s+','',delay[1])) if delay else None,
            route_ns=float(re.sub(r'\s+','',delay[2])) if delay else None))
    return result
def summary(folder):
    text=(folder/'timing.rtr').read_text(errors='replace');res=(folder/'resources.dmr').read_text(errors='replace')
    p=re.search(r'(\d+\.\d+) MHz\s+(\d+\.\d+) MHz',text);assert p
    corners={}
    for name in ('Setup Summary(Slow Corner)','Hold Summary(Slow Corner)','Setup Summary(Fast Corner)','Hold Summary(Fast Corner)'):
        b=text.split(name+':',1)[1].split('====',1)[0];r=re.search(r'\n\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(\d+)\s+(\d+)',b)
        assert r;corners[name]=dict(worst_slack_ns=float(r[1]),failing_endpoints=int(r[3]))
    return dict(estimated_fmax_mhz=float(p[2]),corners=corners,resources={n:int(re.search(r'\| '+re.escape(n)+r'\s+\|\s+(\d+)',res)[1]) for n in ('LUT','FF','Distributed RAM','DRM','APM')})
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--candidate',choices=('aux','head'),required=True);a=ap.parse_args()
    accepted=read(ROOT/'docs/accepted_baseline.json');assert accepted==read(OUT/'before/accepted_baseline.json')
    before=read(OUT/'before/validation/baseline.json');after=read(OUT/'validation/baseline.json');verify(after)
    assert accepted['source_sha256']==before['source_sha256']
    selected=OUT/a.candidate
    for n,h in read(selected/'source_sha256.json').items():assert sha(ROOT/n)==h,n
    changed=sorted(n for n,h in after['source_sha256'].items() if before['source_sha256'].get(n)!=h)
    expected=['hardware/pds/source/core/nc_core.v','hardware/pds/source/core/nc_execute.v']
    if a.candidate=='head':expected+=['hardware/pds/source/core/nc_operands.v']
    assert changed==expected,changed
    reference=read(ROOT/'simulation/results/coremark_performance_10_verilator_ipc_combo/result.json')
    old_inputs={'hardware/pds/source/'+str(p.relative_to(OUT/'before/source')).replace('\\','/'):p for p in (OUT/'before/source').rglob('*.v')}
    verify(reference,old_inputs)
    candidates={}
    for name in ('aux','capture','head'):
        folder=OUT/name;x=read(folder/'coremark.json');override={}
        for rtl in ('nc_core.v','nc_execute.v','nc_operands.v'):override['hardware/pds/source/core/'+rtl]=folder/rtl
        verify(x,override);assert x['status']=='PASS'
        assert x['metrics']==reference['metrics'] and x['predictor']==reference['predictor'] and x['multiply']==reference['multiply'],name
        candidates[name]=dict(pds=summary(folder),cycles=int(x['metrics']['Stats window cycles']),status='RETAINED' if name==a.candidate else 'NOT_RETAINED')
        for n,h in read(folder/'source_sha256.json').items():assert sha(override.get(n,ROOT/n))==h,n
        for n in ('uart.txt','simulation.log'):
            copy(ROOT/f'simulation/results/coremark_performance_10_verilator_exid_{name}'/n,folder/n)
        if name!='aux':
            eq=read(folder/'operands_equiv.json');assert eq['status']=='PASS';verify(eq,override)
            copy(ROOT/f'simulation/results/exid_{name}_equiv.log',folder/'operands_equiv.log')
        save(folder/'paths.json',paths((folder/'timing.rtr').read_text(errors='replace')))
    final=read(ROOT/f'simulation/results/coremark_performance_10_verilator_exid_{a.candidate}/result.json');verify(final)
    valid_folder=ROOT/'simulation/results/coremark_validation_1_verilator_exid_final';valid=read(valid_folder/'result.json');verify(valid)
    assert valid['status']=='PASS' and valid['metrics']['CRC validation']=='PASS'
    assert valid['metrics']==read(ROOT/'simulation/results/coremark_validation_1_verilator_ipc_final/result.json')['metrics']
    assert final['image_sha256']==reference['image_sha256']==sha(ROOT/'sw/build/boot.hex')
    for folder in (ROOT/f'simulation/results/coremark_performance_10_verilator_exid_{a.candidate}',valid_folder):
        for n in ('result.json','uart.txt','simulation.log'):copy(folder/n,OUT/'validation'/f'{folder.name}_{n}')
    suites=['stage_opt','prediction','multiply','fetch_equiv','ex_equiv','pair_model']
    if a.candidate=='head':suites+=['operands_equiv']
    for suite in suites:
        folder=ROOT/'simulation/results'/suite;x=read(folder/'result.json');assert x['status']=='PASS',suite;verify(x)
        for p in folder.iterdir():
            if p.suffix in ('.json','.log'):copy(p,OUT/'validation'/f'{suite}_{p.name}')
    for n in ('regression.json','isa.json'):assert read(ROOT/'simulation/results'/n)==read(OUT/'validation'/n)
    for n,h in after['source_sha256'].items():
        if n.startswith('hardware/pds/source/'):copy(ROOT/n,OUT/'source'/Path(n).relative_to('hardware/pds/source'))
    for n in ('check_execute_equivalence.py','check_operands_equivalence.py','archive_ex_id_finish.py','collect_validation.py','run.ps1'):copy(ROOT/'tools'/n,OUT/'tools'/n)
    for n in ('execute_equivalence_tb.v','operands_equivalence_tb.v'):copy(ROOT/'simulation/tb'/n,OUT/'tests'/n)
    copy(ROOT/'hardware/pds/new_core.tcl',OUT/'validation/new_core.tcl')
    copy(ROOT/'hardware/pds'/f'exid_{a.candidate}_final_build.log',OUT/'validation/pds_build.log')
    for n in ('exid_final_tests.log','exid_final_validation.log'):copy(ROOT/'simulation/results'/n,OUT/'validation'/n)
    save(OUT/'paths.json',paths((OUT/'validation/timing.rtr').read_text(errors='replace')))
    p0=before['pds'];p1=after['pds']
    assert p1['estimated_fmax_mhz']>p0['estimated_fmax_mhz']
    result=dict(status='IMPLEMENTED_AND_VERIFIED',user_accepted=False,date=datetime.now().astimezone().isoformat(),selected_candidate=a.candidate,
        changed_sources=changed,source_sha256=after['source_sha256'],before=p0,after=p1,
        changes=dict(estimated_fmax_percent=(p1['estimated_fmax_mhz']/p0['estimated_fmax_mhz']-1)*100,resources={k:p1['resources'][k]-v for k,v in p0['resources'].items()}),
        candidates=candidates,coremark_metrics_unchanged=True,coremark=final['metrics'],predictor_unchanged=True,multiply_unchanged=True,image_sha256=final['image_sha256'],
        limits=['Same approximately 75 MHz PLL; frequency is a PDS estimate. No bitstream or board run.',
                'No pipeline stage, cycle, RAM bypass, ready cascade or early memory request added.',
                'Successful branch auxiliary payload may differ; MEM exposes it as tval only on an exception.'])
    save(OUT/'comparison.json',result)
    save(OUT/'manifest.json',dict(status='PASS',files_sha256={str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='manifest.json'}))
    print(json.dumps(dict(status='PASS',selected=a.candidate,changes=result['changes'],after=p1),indent=2))
if __name__=='__main__':main()
