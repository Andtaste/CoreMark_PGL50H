"""Sequential physical runs, identical constraints and no seed search."""
from pathlib import Path
import sys,subprocess
ROOT=Path(__file__).resolve().parents[1]
for t in sys.argv[1:]:
 src=ROOT/('simulation/results/load_bp_dual_boundary_next_'+t)
 if not (src/'result.json').exists():print('SKIP missing simulation',t,flush=True);continue
 print('START ROUTE',t,flush=True)
 with (src/'run_pds.log').open('wb') as f:x=subprocess.run([sys.executable,str(ROOT/'tools/research_dual_timing80_pds.py'),'--variant','dual_boundary_next_'+t],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
 print('END ROUTE',t,x.returncode,flush=True)
