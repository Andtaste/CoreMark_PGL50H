"""Use identical dual-LSU harness, with registered completion invariants."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 base=ROOT/'tools/run_dual_lsu.py';s=base.read_text().replace("('dual_lsu_shared','dual_lsu_ports')","('dual_lsu_forward',)")
 ns={'__file__':str(base),'__name__':'forward_runner'};exec(compile(s,str(base),'exec'),ns);ns['main']();phase=sys.argv[sys.argv.index('--phase')+1];src=ROOT/'simulation/results/load_bp_dual_lsu_forward'
 for p in [src/phase/'result.json']+([src/'result.json'] if phase=='performance' else []):
  x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();n='tools/generate_dual_lsu_forward.py';x['input_sha256'][n]=hashlib.sha256((ROOT/n).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
