"""Read back all generated vendor RAM words and check trial physical UART."""
from pathlib import Path
import argparse
from clock_trial_args import parse
ROOT=Path(__file__).resolve().parents[1]
def main():
 a=parse()
 base=ROOT/'tools/check_board5000_io.py';s=base.read_text()
 s=s.replace("ROOT/'hardware/pds_board5000'",f"ROOT/{a.project!r}")
 s=s.replace("ROOT/'simulation/results/board5000_io'",f"ROOT/{a.io!r}")
 s=s.replace("ROOT/'simulation/tb/uart82_tb.v'",f"ROOT/'{a.checks}/uart82_tb.v'")
 s=s.replace("ROOT/'docs/board5000_20261022/io_result.json'",f"ROOT/'{a.io}/result.json'")
 s=s.replace('82000000',str(a.hz)).replace('DIV712','DIV'+str((a.hz+57600)//115200))
 ns={'__file__':str(base),'__name__':'clock_io'};exec(compile(s,str(base),'exec'),ns);ns['main']()
if __name__=='__main__':main()
