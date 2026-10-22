"""Rebuild the final per-lane refinement; the other ten trials have a frozen replay."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];base=ROOT/'tools/verify_dual_next_reproduction.py';s=base.read_text().replace("'aluwake':'generate_dual_next_aluwake.py'","'aluwake':'generate_dual_next_aluwake.py','alulanes':'generate_dual_next_alulanes.py'")
ns={'__file__':str(base),'__name__':'per_lane_exact_replay'};exec(compile(s,str(base),'exec'),ns);ns['TRIALS']=['alulanes'];ns['OUT']=ROOT/'simulation/results/dual_next_reproduction_alulanes';ns['main']();p=ns['OUT']/'result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
