CoreMark fixed-10 image from the adopted pairbranch baseline.
boot.hex: 16384 RV32 words. boot_interleaved.hex: vendor A64/B32 initialization encoding, 8192 entries.
The RAM1 IP INIT_FILE uses boot_interleaved.hex; do not replace it with raw boot.hex.
Both generated INIT parameters and all inverse-decoded words were checked against the accepted baseline.
