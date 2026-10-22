# Run only after verify_clock82_checkpoint.py --install; use tools/build_release.py.
set root [file normalize [file dirname [info script]]]
cd $root
set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484
pnr -input_db_file "$root/device_map/top_map.adf" -gplace_seed 22 -gplace_times 1 -saved_outcome 1 -parallel 1 -groute_seed 4 -groute_times 1 -max_ctrl_chain_length 4 -optimize_multi_corner_timing -fix_hold_violation -fix_hold_violation_in_route TRUE
report_timing -max_path 30 -nworst 1
