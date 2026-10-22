"""Use documented PDS setup-critical net priority routing; no timing exceptions."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'docs/clock82_multiseed_20261022'
dest=ROOT/'hardware/pds82_route_iterate';dest.mkdir(exist_ok=False)
db=ROOT/'hardware/pds82_seed_sweep/place_route/seed_6/top_plc.adf'
opts='-enable_route_constraint_iterate -route_constraint_iterate_times 4 -route_constraint_slack 0.05 -route_constraint_max_timing_path 5'
cmd=f'pnr -input_place_db_file {{{db.as_posix()}}} -gplace_seed 6 -gplace_times 1 -parallel 1 -groute_seed 16 -groute_times 3 -route_seed_step 1 -route_saved_outcome 3 -route_parallel 2 -max_ctrl_chain_length 4 -optimize_multi_corner_timing -fix_hold_violation -fix_hold_violation_in_route TRUE '+opts
tcl=dest/'search.tcl';tcl.write_text('set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\n'+cmd+'\nreport_timing -max_path 30 -nworst 1\n')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=out/'additional_route_plans.json';plans=json.loads(p.read_text());plans.append(dict(place_seed=6,route_seeds=[16,17,18],parallel=2,trial_directory=str(dest.relative_to(ROOT)),placement_db=str(db.relative_to(ROOT)),placement_sha256=sha(db),tcl_sha256=sha(tcl),pnr_command=cmd,pnr_options=opts,documentation='Installed Pango_Design_Suite_User_Guide.pdf pp116-117: automatically prioritize routing of nets below setup threshold; no timing constraint relaxation.'))
p.write_text(json.dumps(plans,indent=2)+'\n');print('Prepared iterative priority-routing seeds16..18')
