"""Audit complete BP study, retain exact source-to-simulation/STA provenance."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def verify(x,sub=None):
    sub=sub or {}
    for kind in ('input_sha256','actual_compile_sha256'):
        for n,h in x.get(kind,{}).items():assert sha(sub.get(n.replace('\\','/'),ROOT/n))==h,n
def main():
    dest=ROOT/'docs/bp_study';dest.mkdir(exist_ok=True)
    accepted=ROOT/'docs/accepted_baseline.json';baseline=read(accepted)
    for n,h in baseline['source_sha256'].items():assert sha(ROOT/n)==h,n;copy(ROOT/n,dest/'production_source'/n)
    assert sha(ROOT/'hardware/pds/report_timing/top.rtr')==sha(ROOT/'docs/ex_id_finish/validation/timing.rtr')
    copy(accepted,dest/'accepted_baseline.json')
    trace=ROOT/'simulation/results/bp_study_trace';collector=read(trace/'result.json');verify(collector)
    screening=read(dest/'screening.json');assert screening['status']=='PASS' and sha(trace/'events.txt.gz')==screening['trace_sha256']
    assert sha(ROOT/'tools/screen_bp_study.py')==screening['tool_sha256']
    assert sha(trace/'result.json')==screening['collector_result_sha256']
    for p in trace.iterdir():
        if p.is_file() and p.suffix in ('.json','.gz','.log','.txt','.v'):copy(p,dest/'trace'/p.name)
    candidates={};basecycles=baseline['coremark_stats_cycles']
    for name in ('bp_fold','bp_ras','bp_combo'):
        folder=ROOT/('simulation/results/load_bp_'+name);out=dest/name
        sim=read(folder/'result.json');validation=read(folder/'validation/result.json');checks=read(folder/'checks/result.json');pds=read(folder/'pds/result.json')
        assert all(x['status']=='PASS' for x in (sim,validation,checks,pds))
        for x,phase in ((sim,'performance'),(validation,'validation')):
            verify(x,{'tools/research_bp_study.py':folder/phase/'tool_snapshot.py'})
            for n,h in x['override_sha256'].items():assert sha(folder/Path(n).name)==h,n
        verify(checks);verify(pds);assert len(checks['tests'])==67
        # LSU control/credits, operand forwarding and EX arithmetic are
        # exactly production. Core changes are only registered RAS hints.
        core=(folder/'nc_core.v' if (folder/'nc_core.v').exists() else ROOT/'hardware/pds/source/core/nc_core.v').read_text()
        assert 'wire ex_fire=execute_valid && mem_credit;' in core
        assert '.out_valid(execute_valid),.out_ready(mem_credit)' in core
        assert 'early_offer' not in core
        for p in folder.iterdir():
            if p.is_file() and p.suffix in ('.v','.json'):copy(p,out/p.name)
        for sub in ('performance','validation','checks'):
            for p in (folder/sub).glob('*'):
                if p.is_file() and p.suffix not in ('.vvp','.elf'):copy(p,out/sub/p.name)
        for n in ('result.json','run.tcl','build.log','report_timing/top.rtr','device_map/top.dmr'):copy(folder/'pds'/n,out/'pds'/n)
        raw=(folder/'pds/report_timing/top.rtr').read_text(errors='replace');paths=[]
        for part in raw.split('Startpoint  : ')[1:6]:
            d=re.search(r'Logic:\s*([\d.]+)ns.*?Route:\s*([\d.]+)ns',part);tco=re.search(r'\btco\b',part)
            data=part[tco.end():part.index('Data arrival time')] if tco else part[:part.index('Data arrival time')]
            paths.append(dict(start=part.splitlines()[0].strip(),end=re.search(r'Endpoint\s+: (.+)',part)[1].strip(),
                slack_ns=float(re.search(r'Slack \(MET\)\s+(-?[\d.]+)',part)[1]),logic_ns=float(d[1]),route_ns=float(d[2]),max_data_fanout=max(map(int,re.findall(r'net \(fanout=(\d+)\)',data)))))
        c=int(sim['metrics']['Stats window cycles']);retired=int(sim['metrics']['Retired instructions']);assert retired==2808261
        candidates[name]=dict(cycles=c,ipc=retired/c,same_clock_gain_percent=(basecycles/c-1)*100,
            estimated_fmax_mhz=pds['estimated_fmax_mhz'],estimated_peak_gain_percent=(basecycles/c*pds['estimated_fmax_mhz']/baseline['estimated_fmax_mhz']-1)*100,
            break_even_fmax_mhz=baseline['estimated_fmax_mhz']*c/basecycles,
            resources=pds['resources'],resource_delta={k:v-baseline['resources'][k] for k,v in pds['resources'].items()},corners=pds['corners'],
            predictor=sim['predictor'],validation_cycles=int(validation['metrics']['Stats window cycles']),tests=67,slow_setup_paths=paths)
    deep={}
    for name in ('bp_ras_deep','bp_combo_deep'):
        folder=ROOT/('simulation/results/load_bp_'+name);x=read(folder/'result.json');assert x['status']=='PASS';verify(x,{'tools/research_bp_study.py':folder/'performance/tool_snapshot.py'})
        for n,h in x['override_sha256'].items():assert sha(folder/Path(n).name)==h,n
        for p in folder.iterdir():
            if p.is_file() and p.suffix in ('.json','.v'):copy(p,dest/'deep_simulation_only'/name/p.name)
        for p in (folder/'performance').iterdir():
            if p.is_file():copy(p,dest/'deep_simulation_only'/name/'performance'/p.name)
        deep[name]=dict(cycles=int(x['metrics']['Stats window cycles']),predictor=x['predictor'],scope='8-entry RAS CoreMark performance simulation only; no PDS/full regression')
    for n in ('collect_bp_study.py','screen_bp_study.py','research_bp_study.py','check_bp_study.py','research_pds.py','archive_bp_study.py'):copy(ROOT/'tools'/n,dest/'tools'/n)
    for n in ('bp_study_trace.vh','bp_study_tb.v','bp_ras_calls.S'):copy(ROOT/'simulation/research'/n,dest/'research'/n)
    report=ROOT/'docs/bp_study.md'
    if report.exists():copy(report,dest/'report.md')
    result=dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',user_accepted=False,baseline=baseline,candidates=candidates,deep_simulation_only=deep,
        production_unchanged=True,accepted_sha256=sha(accepted),production_sta_sha256=sha(ROOT/'hardware/pds/report_timing/top.rtr'),
        limits=['Fixed-schedule screening is not a changed-CPU IPC simulation.',
                'CoreMark images, FPGA device/options/IP/constraints are fixed.',
                'One physical implementation of each selected candidate; no seed sweep or timing exceptions.',
                'Fmax is PDS estimate; actual PLL unchanged at about 75 MHz; no board run.',
                'Extra history/gshare/BHT schemes were screened, not implemented.'])
    decision=dest/'decision.json'
    if decision.exists():result['decision']=read(decision);result['status']=result['decision']['status']
    save(dest/'comparison.json',result)
    save(dest/'manifest.json',{str(p.relative_to(dest)):sha(p) for p in sorted(dest.rglob('*')) if p.is_file() and p.name!='manifest.json'})
    print(json.dumps({k:{n:v for n,v in c.items() if n in ('cycles','ipc','same_clock_gain_percent','estimated_fmax_mhz','estimated_peak_gain_percent','resources')} for k,c in candidates.items()},indent=2))
if __name__=='__main__':main()
