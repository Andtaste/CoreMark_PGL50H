"""Preserve original runners, accepting arbitrary UART bytes during log parsing."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 base=ROOT/'tools/run_dual_boundary_v2.py';s=base.read_text().replace("ns={'__file__':str(base),'__name__':'boundary_v2'};", "s=s.replace(\"(src/phase/'simulation.log').read_text()\",\"(src/phase/'simulation.log').read_text(errors='replace')\")\n ns={'__file__':str(base),'__name__':'boundary_v2'};")
 v=sys.argv[sys.argv.index('--variant')+1];phase=sys.argv[sys.argv.index('--phase')+1];ns={'__file__':str(base),'__name__':'boundary_v3'};exec(compile(s,str(base),'exec'),ns);ns['main']()
 src=ROOT/('simulation/results/load_bp_'+v)
 for p in [src/phase/'result.json']+([src/'result.json'] if phase=='performance' else []):
  x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
