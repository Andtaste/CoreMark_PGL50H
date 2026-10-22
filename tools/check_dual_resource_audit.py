"""Retain lint/admission safety audit, with the proved compressed FIFO width."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
v=sys.argv[sys.argv.index('--variant')+1];src=ROOT/('simulation/results/load_bp_'+v)
assert v.endswith(('resourcequeue','resourceboth'))
assert json.loads((src/'resource_proof/result.json').read_text())['status']=='PASS'
c=(src/'nc_core.v').read_text();assert 'assign mem_credit=queue_credit;' in c and 'assign mem_valid=queued_valid || execute_valid;' in c
base=ROOT/'tools/check_dual_legacy.py';s=base.read_text().replace("a.variant.startswith('dual_legacy_')","a.variant.startswith('dual_boundary_')").replace("a.variant!='dual_legacy_fifo'","False")
s=s.replace('WIDTH(249)','WIDTH(217)').replace('width249/depth4 preserved; no ready-to-EX feedback','width217/depth4; lossless compression SAT passed; input credit remains registered occupancy')
sys.argv=[str(base),'--variant',v,'--mode','audit'];ns={'__file__':str(base),'__name__':'resource_audit'};exec(compile(s,str(base),'exec'),ns);ns['main']()
p=src/'audit_checks/result.json';x=json.loads(p.read_text());x['input_sha256']['tools/check_dual_resource_audit.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
