"""Reuse the closest existing82 placement and vary only three route seeds."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'docs/clock82_multiseed_20261022';s=json.loads((out/'seed_results.json').read_text());assert not s['passing']
closest=max(s['seeds'],key=lambda k:s['seeds'][k]['corners']['Setup Summary(Slow Corner)']['worst_slack_ns']);assert s['seeds'][closest]['corners']['Setup Summary(Slow Corner)']['worst_slack_ns']>=-0.1
folder=ROOT/s['seeds'][closest]['directory'];db=folder/'top_plc.adf';assert db.is_file();dest=ROOT/'hardware/pds82_route_sweep';assert not dest.exists();dest.mkdir()
cmd='pnr -input_place_db_file {'+db.as_posix()+f'}} -gplace_seed {closest} -gplace_times 1 -parallel 1 -groute_seed 1 -groute_times 3 -route_seed_step 1 -route_saved_outcome 3 -route_parallel 3 -max_ctrl_chain_length 4 -optimize_multi_corner_timing -fix_hold_violation -fix_hold_violation_in_route TRUE'
tcl=dest/'route_seeds.tcl';tcl.write_text('set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\n'+cmd+'\nreport_timing -max_path 30 -nworst 1\n')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();x=dict(status='PREPARED',place_seed=int(closest),route_seeds=[1,2,3],trial_directory=str(dest.relative_to(ROOT)),placement_db=str(db.relative_to(ROOT)),placement_sha256=sha(db),tcl_sha256=sha(tcl),pnr_command=cmd,scope='Same genuine82MHz design and saved closest placement; route randomness only, no RTL or constraint edits')
(out/'route_plan.json').write_text(json.dumps(x,indent=2)+'\n');print('PREPARED fixed placement',closest,'route seeds1..3')
