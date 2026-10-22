"""Reuse unchanged PDS options with isolated vendor-generated PLL80 input."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
def main():
 base=ROOT/'tools/research_dual_ram_pds.py';s=base.read_text()
 s=s.replace("folder if ip!='pll' and",'folder if')
 s=s.replace("'production_preserved':", "'production_preserved':")
 s=s.replace('timeout=900','timeout=1800')
 ns={'__file__':str(Path(__file__).resolve()),'__name__':'timing80_pds'}
 exec(compile(s,str(base),'exec'),ns);ns['main']()
if __name__=='__main__':main()
