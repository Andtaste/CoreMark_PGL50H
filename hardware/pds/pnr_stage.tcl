set root [file normalize [file dirname [info script]]]
cd $root
set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484
pnr -input_place_db_file "$root/checkpoints/clock82_place.adf" -gplace_seed 0 -gplace_times 1 -parallel 1 -groute_seed 1 -groute_times 1 -max_ctrl_chain_length 4 -optimize_multi_corner_timing -fix_hold_violation -fix_hold_violation_in_route TRUE
report_timing -max_path 30 -nworst 1
