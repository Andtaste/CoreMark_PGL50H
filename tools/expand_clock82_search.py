"""Prepare additional native PDS searches on genuine82 inputs."""
from pathlib import Path
import json, hashlib
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'docs/clock82_multiseed_20261022'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
arch='set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\n'
opts=' -max_ctrl_chain_length 4 -optimize_multi_corner_timing -fix_hold_violation -fix_hold_violation_in_route TRUE'
db=ROOT/'hardware/pds82_seed_sweep/device_map/top_map.adf'
plc=ROOT/'hardware/pds82_seed_sweep/place_route/seed_6/top_plc.adf'
for kind,first,count,parallel in [('place',20,20,3),('route',4,12,4)]:
    dest=ROOT/f'hardware/pds82_{kind}_extra';dest.mkdir(exist_ok=False)
    if kind=='place':
        cmd=f'pnr -input_db_file {{{db.as_posix()}}} -gplace_seed {first} -gplace_times {count} -seed_step 1 -saved_outcome {count} -parallel {parallel}'+opts
        plan=dict(seeds=list(range(first,first+count)),mapped_input_db=str(db.relative_to(ROOT)),mapped_db_sha256=sha(db))
    else:
        cmd=f'pnr -input_place_db_file {{{plc.as_posix()}}} -gplace_seed 6 -gplace_times 1 -parallel 1 -groute_seed {first} -groute_times {count} -route_seed_step 1 -route_saved_outcome {count} -route_parallel {parallel}'+opts
        plan=dict(place_seed=6,route_seeds=list(range(first,first+count)),placement_db=str(plc.relative_to(ROOT)),placement_sha256=sha(plc))
    tcl=dest/'search.tcl';tcl.write_text(arch+cmd+'\nreport_timing -max_path 30 -nworst 1\n')
    plan.update(trial_directory=str(dest.relative_to(ROOT)),parallel=parallel,tcl_sha256=sha(tcl),pnr_command=cmd)
    (out/f'additional_{kind}_plans.json').write_text(json.dumps([plan],indent=2)+'\n')
    print(kind,first,first+count-1,dest)
