"""Strip the mode argument only when dispatching the standalone pair checker."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 v=sys.argv[sys.argv.index('--variant')+1];mode=sys.argv[sys.argv.index('--mode')+1];base=ROOT/'tools/check_dual_boundary_v2.py';s=base.read_text().replace(" ns={'__file__':str(base),'__name__':'boundary_check_v2'};", " if mode=='pairs':\n  i=sys.argv.index('--mode');del sys.argv[i:i+2]\n ns={'__file__':str(base),'__name__':'boundary_check_v2'};")
 ns={'__file__':str(base),'__name__':'boundary_v3'};exec(compile(s,str(base),'exec'),ns);ns['main']()
 sub='pair_checks' if mode=='pairs' else mode+'_checks';p=ROOT/('simulation/results/load_bp_'+v)/sub/'result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
