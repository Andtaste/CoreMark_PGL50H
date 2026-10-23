set root [file normalize [file dirname [info script]]]
cd $root
set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484
foreach directory {core perips sys_bus top source} {
 foreach src [lsort [glob -directory "$root/source/$directory" *.v]] {add_design $src}
}
foreach ip {pll ram1_tdp ram2_tdp} {add_design "$root/ipcore/$ip/$ip.idf"}
add_constraint "$root/constraints/board.fdc"
compile -top_module top
synthesize -ads -selected_syn_tool_opt 2 -fanout_guide 64
dev_map
pnr -gplace_seed 9 -groute_seed 1 -max_ctrl_chain_length 4 -optimize_multi_corner_timing -fix_hold_violation -enable_route_constraint_iterate -route_constraint_iterate_times 4 -route_constraint_slack 0.05 -route_constraint_max_timing_path 5
report_timing -max_path 30
