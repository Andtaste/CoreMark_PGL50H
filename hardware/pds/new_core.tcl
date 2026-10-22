# Full verified build: python tools/build_release.py from repository root.
# Stage 1: compile and map; stage 2 is guarded by the Python build driver.
# Verified 82MHz target; chosen seed from the frozen multi-seed sweep.
set root [file normalize [file dirname [info script]]]
cd $root
set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484
foreach directory {core perips sys_bus top source} {
 foreach src [lsort [glob -directory "$root/source/$directory" *.v]] {add_design $src}
}
foreach ip {pll ram1_tdp ram2_tdp} {add_design "$root/ipcore/$ip/$ip.idf"}
add_constraint "$root/constraints/board.fdc"
# Default: rebuild RTL, verify exact inputs/connectivity, restore the verified canonical map.
# Keep native stage commands at top level so a clean PDS checkout detects ADS correctly.
compile -top_module top
synthesize -ads -selected_syn_tool_opt 2
dev_map
