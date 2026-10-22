"""Explore a second near-passing placement with a different critical path."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'docs/clock82_multiseed_20261022'
dest=ROOT/'hardware/pds82_route22';dest.mkdir(exist_ok=False)
db=ROOT/'hardware/pds82_place_extra/place_route/seed_22/top_plc.adf'
cmd=f'pnr -input_place_db_file {{{db.as_posix()}}} -gplace_seed 22 -gplace_times 1 -parallel 1 -groute_seed 1 -groute_times 4 -route_seed_step 1 -route_saved_outcome 4 -route_parallel 3 -max_ctrl_chain_length 4 -optimize_multi_corner_timing -fix_hold_violation -fix_hold_violation_in_route TRUE'
tcl=dest/'search.tcl';tcl.write_text('set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\n'+cmd+'\nreport_timing -max_path 30 -nworst 1\n')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=out/'additional_route_plans.json';plans=json.loads(p.read_text());plans.append(dict(place_seed=22,route_seeds=[1,2,3,4],parallel=3,trial_directory=str(dest.relative_to(ROOT)),placement_db=str(db.relative_to(ROOT)),placement_sha256=sha(db),tcl_sha256=sha(tcl),pnr_command=cmd))
tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(plans,indent=2)+'\n');tmp.replace(p);print('Prepared placement22 route1..4')
