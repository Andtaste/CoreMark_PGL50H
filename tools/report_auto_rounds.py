"""Summarize measured candidates; never treat failed 82MHz STA as accepted."""
from pathlib import Path
import hashlib,json,re
from verify_board_pnr import inspect
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'simulation/results/autonomous_20261022'
rows=[]
active=ROOT/'docs/active_optimization_baseline.json'
active_record=json.loads(active.read_text()) if active.exists() else None
base=json.loads((ROOT/'simulation/results/load_bp_dual_boundary_auto_control/performance/result.json').read_text())
basecycles=int(base['metrics']['Benchmark cycles64'])
for d in WORK.iterdir():
 if not (d/'inputs.json').exists():continue
 sim=ROOT/f'simulation/results/load_bp_dual_boundary_auto_{d.name}'
 row={'name':d.name,'decision':'PENDING'}
 derivation=d/'derivation.json'
 if derivation.exists():
  derived=json.loads(derivation.read_text())
  if derived.get('identical_inputs'):
   parent=WORK/derived['parent_trial']
   for n,h in json.loads((d/'inputs.json').read_text()).items():
    assert hashlib.sha256((d/n).read_bytes()).hexdigest()==h
    assert hashlib.sha256((parent/n).read_bytes()).hexdigest()==h
   sim=ROOT/f'simulation/results/load_bp_dual_boundary_auto_{parent.name}'
   row['simulation_source']=parent.name
 for phase in ('checks','performance','validation'):
  p=sim/phase/'result.json'
  if p.exists():
   x=json.loads(p.read_text());row[phase]=x['status']
   if phase=='checks':row['regression_cases']=len(x['tests'])
   if phase=='performance':
    m=x['metrics'];cycles=int(m['Benchmark cycles64']);row.update(benchmark_cycles=cycles,ipc=int(m['Retired instructions'])/int(m['Stats window cycles']),cm_per_mhz=10e6/cycles,same_clock_gain_pct=100*(basecycles/cycles-1))
    if active_record:row['gain_vs_active_pct']=100*(active_record['benchmark_cycles']/cycles-1)
 for label in ('lockstep',):
  p=d/label/'result.json'
  if p.exists():row[label]=json.loads(p.read_text())['status']
 report=d/'report_timing/top.rtr'
 if report.exists():
  text=report.read_text(errors='replace');m=re.search(r'(\d+\.\d+) MHz\s+(\d+\.\d+) MHz',text)
  if m:
   row['estimated_fmax_mhz']=float(m[2]);row['sta']='PASS' if 'All Constraints Met.' in text else 'FAIL'
   row['corners']={}
   for name in ('Setup Summary(Slow Corner)','Hold Summary(Slow Corner)','Setup Summary(Fast Corner)','Hold Summary(Fast Corner)'):
    block=text.split(name+':',1)[1].split('====',1)[0];v=re.search(r'\n\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(\d+)\s+(\d+)',block)
    row['corners'][name]={'slack_ns':float(v[1]),'failing_endpoints':int(v[3])}
   prr=(d/'place_route/top.prr').read_text(errors='replace')
   row['resources']={k:sum(map(int,re.findall(r'^\|\s+'+k+r'\s+\|\s+(\d+)',prr,re.M))) for k in ('LUT','FF','Distributed RAM')}
   for k in ('DRM','APM'):row['resources'][k]=int(re.search(r'^\| Use of '+k+r'\s+\|\s+(\d+)',prr,re.M)[1])
   if row['sta']=='FAIL':row['decision']='REJECT_AT_82MHZ'
   else:
    cached=d/'physical_verification.json'
    if (d/'place_route/top_pnr.adf').exists():
     verified=inspect(d);cached.write_text(json.dumps(verified,indent=2)+'\n')
    else:
     verified=json.loads(cached.read_text())
     assert verified['sta_sha256']==hashlib.sha256(report.read_bytes()).hexdigest()
     assert verified['pnr_report_sha256']==hashlib.sha256((d/'place_route/top.prr').read_bytes()).hexdigest()
    row['verified_board']=verified;row['decision']='ELIGIBLE_FOR_FURTHER_VALIDATION'
   row['sta_sha256']=hashlib.sha256(report.read_bytes()).hexdigest()
 decision_file=d/'decision.json'
 if decision_file.exists():row.update(json.loads(decision_file.read_text()))
 rows.append(row)
for row in rows:
 if row['name']=='control':
  verified=inspect(WORK/'original_board');row.update(decision='PRESERVED_PARENT',estimated_fmax_mhz=verified['estimated_fmax_mhz'],resources=verified['routed_resources'],sta='PASS')
 if active_record and row['name']==active_record.get('source_trial','btb_fold'):row['decision']='ADOPTED'
 elif active_record and (row['name']=='btb_fold' or (WORK/row['name']/'adoption.json').exists()):row['decision']='PRESERVED_PREVIOUS_BASELINE'
save=WORK/'comparison.json';save.write_text(json.dumps({'baseline_project':'hardware/pds_board5000','priority':['throughput','clock_mhz','cm_per_mhz','resources'],'scope':'Fixed10 diagnostic, identical binary, real82MHz board constraints. Seeds from each project; default placement3/route1. No board measurement.','candidates':rows},indent=2)+'\n')
for r in rows: print(r['name'],r.get('cm_per_mhz'),r.get('estimated_fmax_mhz'),r.get('resources'),r['decision'])
