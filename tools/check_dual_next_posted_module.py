"""Replay the existing posted-store contract with explicit disabled pending-side inputs."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
v=sys.argv[sys.argv.index('--variant')+1];base=ROOT/'tools/check_dual_store_ack.py';s=base.read_text()
if v.endswith('loadsplitv2'):s=s.replace('m(.clk(clk),.rst_n(rst_n)',"m(.pending_valid(1'b0),.pending_tag(3'b0),.pending_done(1'b0),.pending_side(65'b0),.clk(clk),.rst_n(rst_n)")
sys.argv=[str(base),'--variant',v,'--mode','module'];ns={'__file__':str(base),'__name__':'pending_disabled_posted_contract'};exec(compile(s,str(base),'exec'),ns);ns['main']()
p=ROOT/('simulation/results/load_bp_'+v+'/posted_module/result.json');x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
