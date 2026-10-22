"""Reuse unchanged external core/bus contracts with new isolated variants."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();base=ROOT/'tools/check_dual_boundary_launch.py';s=base.read_text().replace('dual_boundary_launch',a.variant);ns={'__file__':str(base),'__name__':'simple_contracts'};exec(compile(s,str(base),'exec'),ns);sys.argv=[str(base)];ns['main']()
 for sub in ('memory_checks','address_contract'):
  p=ROOT/('simulation/results/load_bp_'+a.variant)/sub/'result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
