"""Collect final native reports while bounded PDS sweeps are running."""
from pathlib import Path
import subprocess,sys,time,json
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'docs/clock82_multiseed_20261022'
last=None
while True:
 for name in ('collect_clock82_seeds.py','collect_clock82_routes.py'):
  p=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools'/name)],cwd=ROOT,capture_output=True)
  if p.returncode:print(p.stderr.decode(errors='replace'),flush=True);sys.exit(p.returncode)
 s=json.loads((out/'seed_results.json').read_text());r=json.loads((out/'route_results.json').read_text())
 all_cases=[(f'P{k}/R0',v) for k,v in s['seeds'].items()]+[(f"P{v['gplace_seed']}/R{v['groute_seed']}",v) for v in r['routes'].values()]
 closest=max(all_cases,key=lambda kv:kv[1]['corners']['Setup Summary(Slow Corner)']['worst_slack_ns'])
 passing=[(k,v['corners']['Setup Summary(Slow Corner)']['worst_slack_ns']) for k,v in all_cases if v['status']=='PASS']
 result=dict(placements=f"{s['completed']}/{s['planned']}",routes=f"{r['completed']}/{r['planned']}",closest=closest[0],setup=closest[1]['corners']['Setup Summary(Slow Corner)']['worst_slack_ns'],passing=passing)
 if result!=last:print(json.dumps(result),flush=True);last=result
 if s['status']=='COMPLETE' and r['status']=='COMPLETE':break
 time.sleep(20)
