"""Test explicit nofault RAM grant, with unknown/MMIO errors retaining order."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 base=ROOT/'tools/run_dual_lsu.py';s=base.read_text().replace("('dual_lsu_shared','dual_lsu_ports')","('dual_lsu_pair',)")
 s=s.replace('nc_core dut(.s_req_valid','nc_core dut(.d_req_nofault(index(da)>=0),.s_req_valid')
 # The ordinary monitor still enforces response order except where an
 # accepted request explicitly guarantees no late fault for this group.
 s=s.replace('!CPU.memory.primary_safe)', '!CPU.memory.primary_safe && !CPU.memory.guaranteed_primary)')
 ns={'__file__':str(base),'__name__':'pair_runner'};exec(compile(s,str(base),'exec'),ns);ns['main']();phase=sys.argv[sys.argv.index('--phase')+1];src=ROOT/'simulation/results/load_bp_dual_lsu_pair'
 for p in [src/phase/'result.json']+([src/'result.json'] if phase=='performance' else []):
  x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();n='tools/generate_dual_lsu_pair.py';x['input_sha256'][n]=hashlib.sha256((ROOT/n).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
