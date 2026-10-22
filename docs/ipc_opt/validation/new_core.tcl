# Run in this directory: pds_shell.exe -f new_core.tcl
# Reproducible entry point, not copied interactive operation history.
set root [file normalize [file dirname [info script]]]
set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484
foreach directory {core perips sys_bus top source} {
 foreach src [lsort [glob -directory "$root/source/$directory" *.v]] { add_design $src }
}
foreach ip {pll ram1_tdp ram2_tdp} {add_design "$root/ipcore/$ip/$ip.idf"}
add_constraint "$root/constraints/board.fdc"
compile -top_module top
synthesize -ads -selected_syn_tool_opt 2
dev_map
# FF -> distributed-RAM write-data paths can be too short. Repair hold in
# physical routing across corners rather than adding RTL cycles or delays.
pnr -max_ctrl_chain_length 4 -optimize_multi_corner_timing -fix_hold_violation -fix_hold_violation_in_route TRUE
report_timing -max_path 30 -nworst 1
