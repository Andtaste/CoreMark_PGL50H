"""Use documented PDS performance placement/routing mode on the same mapped DB."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'docs/clock82_multiseed_20261022'
dest=ROOT/'hardware/pds82_performance';dest.mkdir(exist_ok=False)
db=ROOT/'hardware/pds82_seed_sweep/device_map/top_map.adf'
opts='-mode performance'
cmd=f'pnr -input_db_file {{{db.as_posix()}}} -gplace_seed 40 -gplace_times 6 -seed_step 1 -saved_outcome 6 -parallel 3 -max_ctrl_chain_length 4 -optimize_multi_corner_timing -fix_hold_violation -fix_hold_violation_in_route TRUE '+opts
tcl=dest/'search.tcl';tcl.write_text('set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\n'+cmd+'\nreport_timing -max_path 30 -nworst 1\n')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=out/'additional_place_plans.json';plans=json.loads(p.read_text());plans.append(dict(seeds=list(range(40,46)),parallel=3,trial_directory=str(dest.relative_to(ROOT)),mapped_input_db=str(db.relative_to(ROOT)),mapped_db_sha256=sha(db),tcl_sha256=sha(tcl),pnr_command=cmd,pnr_options=opts,documentation='Installed Pango_Design_Suite_User_Guide.pdf p108: performance mode prioritizes timing with longer runtime. No RTL/clock/constraint edits.'))
tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(plans,indent=2)+'\n');tmp.replace(p);print('Prepared performance-mode placement seeds40..45')
