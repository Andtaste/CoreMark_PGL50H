"""Reuse actual-top UART and independent fixed-image counters at the trial clock."""
from pathlib import Path
import argparse,json
from clock_trial_args import parse
ROOT=Path(__file__).resolve().parents[1]
def main():
 a=parse();src=ROOT/a.project
 parent=json.loads((src/'parent_baseline.json').read_text())
 reference=parent.get('source_trial','btb_fold')
 base=ROOT/'tools/check_clock82.py';s=base.read_text()
 s=s.replace("ROOT/'hardware/pds82_seed_sweep'",f"ROOT/{a.project!r}")
 s=s.replace("ROOT/'simulation/results/load_bp_dual_boundary_next_pairbranch'",f"ROOT/'simulation/results/load_bp_dual_boundary_auto_{reference}'")
 s=s.replace("ROOT/'simulation/results/clock82_checks'",f"ROOT/{a.checks!r}")
 s=s.replace("ROOT/'hardware/pds'/p.relative_to(src)",f"ROOT/{parent['project_directory']!r}/p.relative_to(src)")
 s=s.replace("b'CLOCK_HZ(80000000)'","b'CLOCK_HZ(PARENT_HZ)'")
 div=(a.hz+57600)//115200
 s=s.replace('82000000',str(a.hz)).replace('712',str(div)).replace('6.097561',f'{500/float(a.frequency):.9f}')
 s=s.replace('PARENT_HZ',str(parent['configured_cpu_hz']))
 # Update report labels without renaming the shared uart82_tb module/file.
 s=s.replace('Physical UART82 exact',f'Physical UART{a.frequency} exact')
 s=s.replace('CLOCK_HZ82 SoC',f'CLOCK_HZ{a.frequency} SoC')
 # Accelerated UART divisor is rounded independently of the physical UART.
 s=s.replace("'localparam UART_DIV=9;'",f"'localparam UART_DIV={(a.hz+4687500)//9375000};'")
 ns={'__file__':str(base),'__name__':'clock_trial_checks'};exec(compile(s,str(base),'exec'),ns);ns['main']()
if __name__=='__main__':main()
