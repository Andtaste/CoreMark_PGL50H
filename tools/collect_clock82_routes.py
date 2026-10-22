"""Collect fixed-placement route variants and choose across all real82 trials."""
from pathlib import Path
import json,hashlib
from collect_clock82_seeds import parse,final_native_result,routed_resources
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'docs/clock82_multiseed_20261022';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plans=[json.loads((out/'route_plan.json').read_text())]
extra=out/'additional_route_plans.json'
if extra.exists():plans+=json.loads(extra.read_text())
records={};planned=0
for plan in plans:
 assert sha(ROOT/plan['placement_db'])==plan['placement_sha256'];folder=ROOT/plan['trial_directory'];planned+=len(plan['route_seeds'])
 for seed in plan['route_seeds']:
  p=folder/f'place_route/seed_{seed}/top.rtr'
  if not p.exists():continue
  try:x=parse(p)
  except (AssertionError,IndexError,ValueError):continue
  if not (p.parent/'top_pnr.adf').exists() or not final_native_result(folder,seed,x):continue
  x.update(gplace_seed=plan['place_seed'],groute_seed=seed,directory=str(p.parent.relative_to(ROOT)),routed_sha256=sha(p.parent/'top_pnr.adf'),pnr_options=plan.get('pnr_options',''),routed_resources=routed_resources(p.parent/'top.prr'))
  key=str(seed) if plan['place_seed']==6 else f"p{plan['place_seed']}_r{seed}"
  assert key not in records,key
  records[key]=x
result=dict(status='COMPLETE' if len(records)==planned else 'RUNNING',completed=len(records),planned=planned,place_seed=6,routes=records,passing=[k for k,x in records.items() if x['status']=='PASS'])
(out/'route_results.json').write_text(json.dumps(result,indent=2)+'\n')
placement=json.loads((out/'seed_results.json').read_text());candidates=[]
for k,x in placement['seeds'].items():
 if x['status']=='PASS':candidates.append(dict(x,gplace_seed=int(k),groute_seed=0,case='place_'+k))
for k,x in records.items():
 if x['status']=='PASS':candidates.append(dict(x,case=f"place_{x['gplace_seed']}_route_{x['groute_seed']}"))
if placement['status']=='COMPLETE' and result['status']=='COMPLETE':
 chosen=max(candidates,key=lambda x:(x['corners']['Setup Summary(Slow Corner)']['worst_slack_ns'],min(v['worst_slack_ns'] for n,v in x['corners'].items() if n.startswith('Hold')))) if candidates else None
 (out/'selected_config.json').write_text(json.dumps(dict(status='COMPLETE',chosen=chosen,passing_cases=[x['case'] for x in candidates]),indent=2)+'\n')
print(json.dumps(dict(status=result['status'],completed=len(records),passing=result['passing'],results={k:dict(setup=x['corners']['Setup Summary(Slow Corner)']['worst_slack_ns'],state=x['status']) for k,x in records.items()}),indent=2))
