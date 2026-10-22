"""Replay unchanged ALU model/timeline contracts for independent per-lane eligibility."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];mode=sys.argv[1];src=ROOT/'simulation/results/load_bp_dual_boundary_next_alulanes'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if mode=='operands':
 base=ROOT/'tools/check_dual_next_alu_operands.py';s=base.read_text().replace("v='dual_boundary_next_aluwake'","v='dual_boundary_next_alulanes'");ns={'__file__':str(base),'__name__':'per_lane_operand_replay'};exec(compile(s,str(base),'exec'),ns);receipt=src/'operands_checks/result.json'
elif mode=='timeline':
 base=ROOT/'tools/check_dual_next_alu_timeline.py';s=base.read_text().replace('load_bp_dual_boundary_next_aluwake','load_bp_dual_boundary_next_alulanes');ns={'__file__':str(base),'__name__':'per_lane_timeline_replay'};exec(compile(s,str(base),'exec'),ns);receipt=src/'timeline_checks/result.json'
elif mode=='proof':
 ref=ROOT/'simulation/results/load_bp_dual_boundary_next_aluwake';evidence=ref/'alu_control_proof/result.json';assert sha(src/'nc_execute.v')==sha(ref/'nc_execute.v');assert json.loads(evidence.read_text())['status']=='PASS';out=src/'alu_control_proof';out.mkdir(exist_ok=True);receipt=out/'result.json';receipt.write_text(json.dumps(dict(status='PASS',tests=['Exact EX bytes reuse two arbitrary-input SAT proofs: ALU data cannot alter control/address fields and original-data EX equivalence'],scope='Explicit exact-hash local proof reuse; operand eligibility differs and is separately simulated in this candidate',input_sha256={str(p.relative_to(ROOT)):sha(p) for p in [src/'nc_execute.v',ref/'nc_execute.v',evidence]}),indent=2)+'\n')
else:raise ValueError(mode)
x=json.loads(receipt.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__));receipt.write_text(json.dumps(x,indent=2)+'\n')
