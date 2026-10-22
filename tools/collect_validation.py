"""Archive evidence for the current RTL/firmware, reject stale STA inputs."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,re,hashlib,shutil,argparse
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='docs/validation')
    args=parser.parse_args()
    out=ROOT/args.output;out.mkdir(parents=True,exist_ok=True)
    timing=ROOT/'hardware/pds/report_timing/top.rtr';text=timing.read_text(errors='replace')
    assert 'All Constraints Met.' in text
    resource=(ROOT/'hardware/pds/device_map/top.dmr').read_text(errors='replace')
    perf=re.search(r'(\d+\.\d+) MHz\s+(\d+\.\d+) MHz\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(-?\d+\.\d+)',text)
    assert perf
    sources=list((ROOT/'hardware/pds/source').rglob('*.v'))
    sources+=list((ROOT/'hardware/pds/ipcore').rglob('*.idf'))
    sources += [ROOT/'sw/build/boot.hex',ROOT/'hardware/pds/constraints/board.fdc',ROOT/'hardware/pds/new_core.tcl']
    for f in sources:assert f.stat().st_mtime<=timing.stat().st_mtime,f'STA older than {f}'
    hashes={str(f.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(sources)}
    summary={}
    for section in ('Setup Summary(Slow Corner)','Hold Summary(Slow Corner)','Setup Summary(Fast Corner)','Hold Summary(Fast Corner)'):
        block=text.split(section+':',1)[1].split('====',1)[0]
        row=re.search(r'\n\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(\d+)\s+(\d+)',block)
        assert row,section
        summary[section]={'worst_slack_ns':float(row[1]),'failing_endpoints':int(row[3])}
    paths=[]
    for block in text.split('Startpoint  : ')[1:]:
        if 'max (slow corner)' not in block:continue
        endpoint=re.search(r'Endpoint\s+: ([^\n]+)',block)
        slack=re.search(r'Slack \((?:MET|VIOLATED)\)\s+(-?\d+\.\d+)',block)
        if endpoint and slack:paths.append({'start':block.splitlines()[0],'end':endpoint[1],'slack_ns':float(slack[1])})
        if len(paths)==5:break
    checks=json.loads((ROOT/'simulation/results/regression.json').read_text())
    isa=json.loads((ROOT/'simulation/results/isa.json').read_text())
    assert len(checks['results'])==14 and len(isa['results'])==47
    assert all(x['status']=='PASS' for x in checks['results']+isa['results'])
    metrics={k:int(re.search(r'\| '+re.escape(k)+r'\s+\|\s+(\d+)',resource)[1]) for k in ('LUT','FF','Distributed RAM','DRM','APM')}
    predicts=bool(re.search(r'parameter\s+ENABLE_BP\s*=\s*1', (ROOT/'hardware/pds/source/core/nc_core.v').read_text()))
    architecture='Original five-stage RV32IM single issue; '+('64-entry tagged BTB with two-bit direction counters; ' if predicts else 'no BTB; ')+'in-order tagged forwarding and retirement'
    if predicts and 'reg[4:0] directions[0:63]' in (ROOT/'hardware/pds/source/core/nc_btb.v').read_text():
        architecture+='; one-bit resolved local history selects two two-bit counters per BTB entry'
    pipelined_mul=(ROOT/'hardware/pds/source/core/nc_mul_pipeline.v').is_file()
    if pipelined_mul:architecture+='; overlapped pipelined multiply with in-order completion'
    result={'date':datetime.now(timezone(timedelta(hours=8))).isoformat(),
        'architecture':architecture,
        'pds':{'requested_mhz':float(perf[1]),'estimated_fmax_mhz':float(perf[2]),'all_reported_constraints_met':True,
               'corners':summary,'resources':metrics,'worst_paths':paths},
        'functional':{'regression_cases':14,'inherited_isa_cases':47,
                      'random_differential_retirements':sum(x.get('differential_retirements',0) for x in checks['results'] if 'random_' in x['test']),
                      'throughput':next(x for x in checks['results'] if x['test']=='soc_throughput'),
                      'uart_demo':next(x for x in checks['results'] if x['test']=='soc_demo_uart')},
        'source_sha256':hashes,
        'limits':['One default PDS implementation, not a guaranteed board Fmax.',
                  'No board download or bitstream generation.',
                  'External IO timing and complete CDC/signoff are not covered; unused RX/JTAG inputs are unconstrained.',
                  'Functional RAM models, not vendor timing simulation; no complete ISA/privileged certification.',
                  ('Pipelined multiply; blocking iterative division; ' if pipelined_mul else 'Blocking multicycle multiply/divide; ')+
                  'single outstanding data transaction; no nonblocking LSU.']}
    for src,name in [(timing,'timing.rtr'),(ROOT/'hardware/pds/device_map/top.dmr','resources.dmr'),
       (ROOT/'hardware/pds/synthesize/apm_drm_lutram_utilization.log','ip_mapping.log'),
       (ROOT/'simulation/results/regression.json','regression.json'),(ROOT/'simulation/results/isa.json','isa.json')]:shutil.copy2(src,out/name)
    (out/'baseline.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'pds':result['pds'],'functional':result['functional']},indent=2))
if __name__=='__main__':main()
