"""Audit and archive the two isolated full-CPU early-load candidates."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
    dest=ROOT/'docs/early_load_integration';dest.mkdir(parents=True,exist_ok=True)
    accepted=ROOT/'docs/accepted_baseline.json';baseline=json.loads(accepted.read_text());cases={}
    def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
    for n,h in baseline['source_sha256'].items():
        assert sha(ROOT/n)==h,n;copy(ROOT/n,dest/'production_source'/n)
    copy(accepted,dest/'accepted_baseline.json')
    assert sha(ROOT/'hardware/pds/report_timing/top.rtr')==sha(ROOT/'docs/ex_id_finish/validation/timing.rtr')
    for variant in ('early_load','early_load_predecode'):
        folder=ROOT/('simulation/results/load_bp_'+variant);out=dest/variant
        sim=json.loads((folder/'result.json').read_text());validation=json.loads((folder/'validation/result.json').read_text())
        checks=json.loads((folder/'integration_checks/result.json').read_text());timing=json.loads((folder/'pds/result.json').read_text())
        injected=json.loads((folder/'injected_fault/result.json').read_text())
        assert all(x['status']=='PASS' for x in (sim,validation,checks,timing,injected))
        for result in (sim,validation):
            for n,h in result['input_sha256'].items():assert sha(ROOT/n)==h,n
            for n,h in result['override_sha256'].items():assert sha(folder/Path(n).name)==h,n
            for n,h in result['actual_compile_sha256'].items():assert sha(ROOT/n)==h,n
        for result in (checks,timing,injected):
            for n,h in result['input_sha256'].items():assert sha(ROOT/n)==h,n
        assert len(checks['tests'])==64,len(checks['tests'])
        assert all(p['baseline_ex_bubbles']==2 for p in checks['directed_pairs'])
        for n in ('nc_core.v','nc_operands.v','nc_memory.v','nc_uart_sim.v','soc_tb_sim.v','result.json'):
            copy(folder/n,out/n)
        for sub in ('performance','validation','integration_checks','injected_fault'):
            for p in (folder/sub).glob('*'):
                if p.is_file() and p.suffix not in ('.vvp','.elf'):copy(p,out/sub/p.name)
        for n in ('result.json','run.tcl','build.log','report_timing/top.rtr','device_map/top.dmr'):
            copy(folder/'pds'/n,out/'pds'/n)
        raw=(folder/'pds/report_timing/top.rtr').read_text(errors='replace')
        paths=[]
        for part in raw.split('Startpoint  : ')[1:6]:
            route=re.search(r'Logic:\s*([\d.]+)ns.*?Route:\s*([\d.]+)ns',part)
            tco=re.search(r'\btco\b',part)
            data_path=part[tco.end():part.index('Data arrival time')] if tco else part[:part.index('Data arrival time')]
            paths.append(dict(startpoint=part.splitlines()[0].strip(),endpoint=re.search(r'Endpoint\s+: (.+)',part)[1].strip(),
                slack_ns=float(re.search(r'Slack \(MET\)\s+(-?[\d.]+)',part)[1]),
                logic_ns=float(route[1]),route_ns=float(route[2]),max_data_net_fanout=max(map(int,re.findall(r'net \(fanout=(\d+)\)',data_path)))))
        cycles=int(sim['metrics']['Stats window cycles']);retired=int(sim['metrics']['Retired instructions'])
        assert retired==2808261 and cycles==3591039
        cases[variant]=dict(cycles=cycles,retired=retired,ipc=retired/cycles,
            same_clock_gain_percent=(baseline['coremark_stats_cycles']/cycles-1)*100,
            estimated_fmax_mhz=timing['estimated_fmax_mhz'],
            estimated_peak_gain_percent=(baseline['coremark_stats_cycles']/cycles*timing['estimated_fmax_mhz']/baseline['estimated_fmax_mhz']-1)*100,
            resources=timing['resources'],resource_delta={k:v-baseline['resources'][k] for k,v in timing['resources'].items()},
            corners=timing['corners'],early_load=sim['early_load'],validation_cycles=int(validation['metrics']['Stats window cycles']),
            tests=len(checks['tests'])+len(injected['tests']),random_delay_coverage=checks['core_random_delay_coverage'],directed_pairs=checks['directed_pairs'],slow_setup_paths=paths)
    for p in [ROOT/'tools'/n for n in ('research_early_load.py','check_early_load.py','check_early_load_fault.py','research_pds.py','archive_early_load.py')]+[ROOT/'simulation/research/early_load_observer.vh',ROOT/'simulation/research/early_load_fault.S']:
        copy(p,dest/'tools'/p.name)
    report=ROOT/'docs/early_load_integration.md'
    if report.exists():copy(report,dest/'report.md')
    result=dict(status='RESEARCH_ONLY_NOT_ADOPTED',user_accepted=False,production_unchanged=True,
        baseline={k:baseline[k] for k in ('name','estimated_fmax_mhz','coremark_stats_cycles','ipc','resources')},
        break_even_fmax_mhz=baseline['estimated_fmax_mhz']*3591039/baseline['coremark_stats_cycles'],candidates=cases,
        accepted_sha256=sha(accepted),production_sta_sha256=sha(ROOT/'hardware/pds/report_timing/top.rtr'))
    decision=dest/'decision.json'
    if decision.exists():
        result['decision']=json.loads(decision.read_text(encoding='utf-8'))
        result['status']=result['decision']['status']
    save(dest/'comparison.json',result)
    save(dest/'manifest.json',{str(p.relative_to(dest)):sha(p) for p in sorted(dest.rglob('*')) if p.is_file() and p.name!='manifest.json'})
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
