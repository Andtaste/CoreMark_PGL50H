# Full native flow with live board constraints; use the Python build driver to generate a checked bitstream.
set root [file normalize [file dirname [info script]]]
source "$root/pnr_stage.tcl"
