"""Repeat the passing place22/route4 from a pinned, byte-identical mapped DB."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'docs/clock82_multiseed_20261022'
dest=ROOT/'hardware/pds82_repeat_p22r4';dest.mkdir(exist_ok=False)
src=ROOT/'hardware/pds82_seed_sweep/device_map/top_map.adf';db=dest/'clock82_map.adf';shutil.copyfile(src,db)
cmd=f'pnr -input_db_file {{{db.as_posix()}}} -gplace_seed 22 -gplace_times 1 -saved_outcome 1 -parallel 1 -groute_seed 4 -groute_times 1 -max_ctrl_chain_length 4 -optimize_multi_corner_timing -fix_hold_violation -fix_hold_violation_in_route TRUE'
tcl=dest/'reproduce.tcl';tcl.write_text('set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\n'+cmd+'\nreport_timing -max_path 30 -nworst 1\n')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(db)==sha(src)
(out/'reproduction_plan.json').write_text(json.dumps(dict(trial_directory=str(dest.relative_to(ROOT)),mapped_input_db=str(db.relative_to(ROOT)),mapped_db_sha256=sha(db),tcl_sha256=sha(tcl),pnr_command=cmd,reason='Independent full placement+route repeat on the same pinned mapped DB. A fresh synthesis can permute128 equivalent RF read-replica instance names and invalidate seed reproducibility.'),indent=2)+'\n')
