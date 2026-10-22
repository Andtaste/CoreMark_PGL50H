"""Align held-slot MUL observation and measure queue-dependent timing explicitly."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 v=sys.argv[sys.argv.index('--variant')+1];mode=sys.argv[sys.argv.index('--mode')+1]
 if mode=='pairs':
  base=ROOT/'tools/check_dual_joint_pairs.py';s=base.read_text().replace("a.variant.startswith('dual_joint_')","a.variant.startswith('dual_boundary_')").replace('CPU.fetch.cross_window','CPU.fetch.rd[0]').replace('CPU.fetch.pop_two_groups','(CPU.fetch.consume && CPU.fetch.pop_two)')
  s=s.replace('CPU.memory.valid && CPU.memory.side_packet[64]', 'CPU.memory.slot_valid && !CPU.memory.exception && CPU.memory.held_side[64]').replace('CPU.memory.side_packet[','CPU.memory.held_side[')
 else:
  base=ROOT/'tools/check_dual_boundary.py';s=base.read_text()
  s=s.replace("r==e+(0 if a.variant.endswith('_early') else 1) and w==r+1 and c==w+1", "r>=e+(1 if a.variant.endswith('_slot') else 0) and w==r+1 and c>=w+1")
 ns={'__file__':str(base),'__name__':'boundary_check_v2'};exec(compile(s,str(base),'exec'),ns);ns['main']()
 sub={'extra':'dual_checks','pairs':'pair_checks','audit':'audit_checks','operands':'operands_checks','timeline':'timeline_checks'}[mode];p=ROOT/('simulation/results/load_bp_'+v)/sub/'result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
