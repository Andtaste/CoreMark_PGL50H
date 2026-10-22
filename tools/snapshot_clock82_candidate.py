"""Freeze the first full-corner passing config for independent main rebuild."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'docs/clock82_multiseed_20261022'
x=json.loads((out/'route_results.json').read_text())['routes']['p22_r4'];assert x['status']=='PASS'
p=out/'candidate_p22_r4.json';assert not p.exists();p.write_text(json.dumps(dict(status='PASSING_CANDIDATE_SEARCH_CONTINUES',chosen=x,scope='Independent main rebuild may proceed while remaining bounded seed searches finish; adoption requires final native main STA.'),indent=2)+'\n')
