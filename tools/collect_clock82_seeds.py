"""Read every completed native seed result; select only full-corner 82MHz passes."""
from pathlib import Path
import json,re,hashlib,csv
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def routed_resources(p):
 text=p.read_text(errors='replace')
 return dict(LUT=sum(map(int,re.findall(r'\|\s+LUT\s+\|\s+(\d+)',text))),FF=sum(map(int,re.findall(r'\|\s+FF\s+\|\s+(\d+)',text))),**{'Distributed RAM':int(re.search(r'\|\s+Distributed RAM\s+\|\s+(\d+)',text)[1]),'DRM':int(re.search(r'\| Use of DRM\s+\|\s+(\d+)',text)[1]),'APM':int(re.search(r'\| Use of APM\s+\|\s+(\d+)',text)[1])})

def final_native_result(folder,seed,result):
 # PDS emits a timing report before the final DB and dispatcher row. Only
 # accept a finished row whose four corner numbers match the native report.
 table=folder/'place_route/multiseed_result.csv'
 if not table.exists():return False
 for row in csv.DictReader(table.read_text(errors='replace').splitlines()):
  if row.get('Seed')!=str(seed) or row.get('State')!='OK':continue
  groups=(('Setup(Slow)','Setup Summary(Slow Corner)'),('Setup(Fast)','Setup Summary(Fast Corner)'),('Hold(Slow)','Hold Summary(Slow Corner)'),('Hold(Fast)','Hold Summary(Fast Corner)'))
  return all(abs(float(row[c])-result['corners'][g]['worst_slack_ns'])<0.0001 for c,g in groups)
 return False
def parse(p):
 text=p.read_text(errors='replace');corners={}
 for name in ('Setup Summary(Slow Corner)','Hold Summary(Slow Corner)','Setup Summary(Fast Corner)','Hold Summary(Fast Corner)'):
  b=text.split(name+':',1)[1].split('====',1)[0];s=re.search(r'\n\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(\d+)\s+(\d+)',b);assert s,(p,name)
  corners[name]=dict(worst_slack_ns=float(s[1]),failing_endpoints=int(s[3]))
 m=re.search(r'(\d+\.\d+) MHz\s+(\d+\.\d+) MHz\s+(\d+\.\d+)\s+(\d+\.\d+)',text);assert m,p
 assert abs(float(m[1])-82)<0.01 and abs(float(m[3])-1000/82)<0.001,(p,m.groups())
 # Native multi-seed reports include unconstrained board-output paths without
 # a slack field. Keep summary checks authoritative; list constrained slow
 # setup paths only, instead of treating an unreported slack as zero/pass.
 critical=[]
 for part in text.split('Startpoint  : ')[1:]:
  slack=re.search(r'Slack \((?:MET|VIOLATED)\)\s+(-?[\d.]+)',part);delay=re.search(r'Logic:\s*([\d.]+)ns.*?Route:\s*([\d.]+)ns',part)
  if not slack or not delay or not re.search(r'Path Type\s+: max \(slow corner\)',part):continue
  critical.append(dict(start=part.splitlines()[0].strip(),end=re.search(r'Endpoint\s+: (.+)',part)[1].strip(),slack_ns=float(slack[1]),logic_ns=float(delay[1]),route_ns=float(delay[2]),logic_levels=int(re.search(r'Logic Levels:\s*(\d+)',part)[1])))
 critical.sort(key=lambda x:x['slack_ns'])
 return dict(status='PASS' if 'All Constraints Met.' in text and all(c['worst_slack_ns']>=0 and c['failing_endpoints']==0 for c in corners.values()) else 'TIMING_FAILED',requested_mhz=float(m[1]),requested_period_ns=float(m[3]),estimated_fmax_mhz=float(m[2]),corners=corners,sta_sha256=sha(p),critical_paths=critical[:3])
def main():
 trial=ROOT/'hardware/pds82_seed_sweep';out=ROOT/'docs/clock82_multiseed_20261022';records={};options={}
 plan=[(trial,k) for k in range(10)]
 extension=out/'extension_plan.json'
 if extension.exists():
  extra=json.loads(extension.read_text());plan +=[(ROOT/extra['trial_directory'],k) for k in extra['seeds']]
 additional=out/'additional_place_plans.json'
 if additional.exists():
  for extra in json.loads(additional.read_text()):
   assert sha(ROOT/extra['mapped_input_db'])==extra['mapped_db_sha256']
   plan +=[(ROOT/extra['trial_directory'],k) for k in extra['seeds']]
   options[str(ROOT/extra['trial_directory'])]=extra.get('pnr_options','')
 for folder,seed in plan:
  p=folder/f'place_route/seed_{seed}/top.rtr'
  if not p.exists():continue
  try:x=parse(p)
  except (AssertionError,IndexError,ValueError):continue
  if not (p.parent/'top_pnr.adf').exists() or not final_native_result(folder,seed,x):continue
  x['routed_sha256']=sha(p.parent/'top_pnr.adf');x['directory']=str(p.parent.relative_to(ROOT));x['pnr_options']=options.get(str(folder),'');x['routed_resources']=routed_resources(p.parent/'top.prr');records[str(seed)]=x
 passing=[int(k) for k,x in records.items() if x['status']=='PASS'];best=max(passing,key=lambda k:(records[str(k)]['corners']['Setup Summary(Slow Corner)']['worst_slack_ns'],min(v['worst_slack_ns'] for n,v in records[str(k)]['corners'].items() if n.startswith('Hold')))) if passing else None
 status='COMPLETE' if len(records)==len(plan) else 'RUNNING';result=dict(status=status,planned=len(plan),completed=len(records),passing=passing,best_seed=best,seeds=records,selection='All timing constraints plus both-corner setup/hold pass at actual 82MHz PLL; maximize slow setup, then minimum hold. No failing seed can be selected.')
 (out/'seed_results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=status,completed=len(records),passing=passing,best_seed=best,results={k:dict(state=x['status'],setup=x['corners']['Setup Summary(Slow Corner)']['worst_slack_ns'],hold=min(v['worst_slack_ns'] for n,v in x['corners'].items() if n.startswith('Hold'))) for k,x in records.items()}),indent=2))
if __name__=='__main__':main()
