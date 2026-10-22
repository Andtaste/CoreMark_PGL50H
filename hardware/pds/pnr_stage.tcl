set root [file normalize [file dirname [info script]]]
# Keep board.fdc in the same PDS process through placement and routing.
source "$root/rebuild_stage.tcl"
pnr -gplace_seed 3 -groute_seed 1 -optimize_multi_corner_timing -fix_hold_violation -max_ctrl_chain_length 4
report_timing -max_path 30
