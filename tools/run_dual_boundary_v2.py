"""Update the old MUL-head observer for the new uniform MEM slot."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 base=ROOT/'tools/run_dual_boundary.py';s=base.read_text().replace("p.read_text().replace('endmodule',mon", "p.read_text().replace('dut.cpu.mem_valid && dut.cpu.memory.input_multiply && !dut.cpu.memory.state &&', 'dut.cpu.memory.slot_valid && dut.cpu.memory.multiply_access &&').replace('endmodule',mon")
 variant=sys.argv[sys.argv.index('--variant')+1];phase=sys.argv[sys.argv.index('--phase')+1];src=ROOT/('simulation/results/load_bp_'+variant)
 ns={'__file__':str(base),'__name__':'boundary_v2'};exec(compile(s,str(base),'exec'),ns);ns['main']()
 for p in [src/phase/'result.json']+([src/'result.json'] if phase=='performance' else []):
  x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
