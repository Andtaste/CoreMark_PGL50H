DDR compatibility for PDS2025

PDS2025 cannot decrypt the original PANGO_V1.1 protected DDR RTL.
The bundled ddr3_test_syn.vm is produced by licensed PDS2022.2-SP1-Lite ADS synthesis of the unmodified DDR source list, with I/O insertion disabled.
PDS2025 uses this netlist for full SoC synthesis and routing. Original IP configuration and source hashes are checked by board_games_pds2025.py.
To regenerate only this block, run E:/pango/PDS_2022.2-SP1-Lite/bin/pds_shell.exe -f rebuild_ddr.tcl from this directory.
The result is rebuild/synthesize/ddr3_test_syn.vm. Review and update manifest hashes before adoption.
No new physical-board DDR training validation is claimed.
