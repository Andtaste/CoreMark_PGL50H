"""Exact-frequency identifiers shared by isolated physical-clock experiments."""
from fractions import Fraction
import argparse,re
def parse():
 p=argparse.ArgumentParser();p.add_argument('--mhz',required=True);p.add_argument('--suffix',default='');p.add_argument('--active-compiler',action='store_true');a=p.parse_args()
 assert re.fullmatch(r'\d+(\.\d+)?',a.mhz)
 assert not a.suffix or re.fullmatch('[a-z0-9_]+',a.suffix)
 a.frequency=Fraction(a.mhz);hz=a.frequency*1000000;assert hz.denominator==1 and hz>0
 a.hz=int(hz);a.label=a.mhz.replace('.','p')+('_'+a.suffix if a.suffix else '')
 ratio=a.frequency/5;a.ratio_i=ratio.denominator;a.ratio_f=ratio.numerator
 a.project=f'simulation/results/continuous_clock{a.label}_20261022'
 a.checks=f'simulation/results/continuous_clock{a.label}_checks';a.io=f'simulation/results/continuous_clock{a.label}_io'
 return a
