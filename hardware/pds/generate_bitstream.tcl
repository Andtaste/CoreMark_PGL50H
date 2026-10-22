set root [file normalize [file dirname [info script]]]
cd $root
set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484
gen_bit_stream -force_to_run -input_db_file "$root/place_route/top_pnr.adf"
