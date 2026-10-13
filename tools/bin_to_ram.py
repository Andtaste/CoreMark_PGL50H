"""Convert CoreMark's little-endian BIN into the PDS ram1 HEX image."""
from pathlib import Path
import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("binary", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
data = args.binary.read_bytes()
if not 0 < len(data) <= 65536:
    parser.error("BIN must contain 1..65536 bytes for the 64 KiB ram1")
padded = data + bytes(65536 - len(data))
lines = [f"{int.from_bytes(padded[i:i+4], 'little'):08X}\n"
         for i in range(0, 65536, 4)]
args.output.write_text("".join(lines), encoding="ascii")
print(f"RAM_INIT_OK: {len(data)} BIN bytes, {len(lines)} words -> {args.output}")
