"""Collect all real-clock/seed trials without accepting timing failures."""
from pathlib import Path
import hashlib,json,re
from verify_board_pnr import inspect
ROOT=Path(__file__).resolve().parents[1]
rows=[]
for d in sorted((ROOT/'simulation/results').glob('continuous_clock*_20261022')):
 meta=json.loads((d/'prepared.json').read_text());report=d/'report_timing/top.rtr'
 row=dict(project=str(d.relative_to(ROOT)),mhz=meta['cpu_hz']/1e6,place_seed=meta.get('place_seed',3),route_seed=meta.get('route_seed',1),status='RUNNING')
 if 'strategy' in meta:
  row['strategy']=meta['strategy'];row['changed_option']=meta['changed_option']
  project=(d/'new_core.pds').read_text()
  for key,value in meta['changed_option'].items():
   assert f'(_option {key} (_integer {value}))' in project,(d.name,key)
 native_log=(d/'native_build.log').read_text(errors='replace') if (d/'native_build.log').exists() else ''
 if (d/'interruption.json').exists():
  row.update(json.loads((d/'interruption.json').read_text()))
  (d/'evaluation.json').write_text(json.dumps(row,indent=2)+'\n')
 if 'Flow-0186' in native_log and 'Program Error Out.' in native_log:
  row['status']='INVALID_CONFIGURATION'
  row['reason']='Tool rejected an out-of-range option before PnR; not a timing result.'
  (d/'evaluation.json').write_text(json.dumps(row,indent=2)+'\n')
 if report.exists() and 'Process "Report Timing" done.' in (d/'native_build.log').read_text(errors='replace'):
  text=report.read_text(errors='replace');m=re.search(r'(\d+\.\d+) MHz\s+(\d+\.\d+) MHz',text);assert m and abs(float(m[1])-row['mhz'])<.01
  row['estimated_fmax_mhz']=float(m[2]);row['status']='PASS' if 'All Constraints Met.' in text else 'FAIL'
  row['corners']={}
  for name in ('Setup Summary(Slow Corner)','Hold Summary(Slow Corner)','Setup Summary(Fast Corner)','Hold Summary(Fast Corner)'):
   block=text.split(name+':',1)[1].split('====',1)[0];v=re.search(r'\n\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(\d+)\s+(\d+)',block)
   row['corners'][name]={'slack_ns':float(v[1]),'failing_endpoints':int(v[3])}
  row['sta_sha256']=hashlib.sha256(report.read_bytes()).hexdigest()
  for n,h in meta['input_sha256'].items():assert hashlib.sha256((d/n).read_bytes()).hexdigest()==h,n
  if meta.get('strategy')=='critical_region':
   assert not re.search(r'^E:',native_log,re.M),'Physical constraint flow contains errors'
   accepted=re.findall(r'Executing : def_inst_region \{([^}]+)\} frontend_critical successfully',native_log)
   assert set(accepted)==set(meta['region']['cells']), 'Region constraints not applied'
   row['region_cells_applied']=len(accepted)
  if row['status']=='PASS':
   if (d/'place_route/top_pnr.adf').exists():row['verified']=inspect(d,row['mhz'])
   else:
    verified=json.loads((d/'evaluation.json').read_text())['verified']
    assert verified['sta_sha256']==row['sta_sha256']
    assert verified['pnr_report_sha256']==hashlib.sha256((d/'place_route/top.prr').read_bytes()).hexdigest()
    row['verified']=verified
  (d/'evaluation.json').write_text(json.dumps(row,indent=2)+'\n')
 rows.append(row)
 for_print={k:v for k,v in row.items() if k not in ('verified','corners','sta_sha256')};print(json.dumps(for_print))
(ROOT/'simulation/results/autonomous_20261022/clock_comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
