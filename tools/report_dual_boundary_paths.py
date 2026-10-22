"""Collect address/write/return and memory control paths from routed boundaries."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 base=ROOT/'tools/report_dual_lsu_ram_paths.py';s=base.read_text().replace("'dual_lsu_[a-z]+'","'dual_boundary_[a-z]+'" ).replace("out=src/'lsu_paths'","out=src/'boundary_paths'")
 s=s.replace(" 'ram_address':", " 'ram_write':' -to {soc/bus/ram_code/*/DB* soc/bus/ram_data/*/DB* soc/bus/ram_code/*/CEB* soc/bus/ram_data/*/CEB*}',\n 'ram_address':")
 ns={'__file__':str(base),'__name__':'boundary_paths'};exec(compile(s,str(base),'exec'),ns);ns['main']();v=sys.argv[-1];p=ROOT/('simulation/results/load_bp_'+v+'/boundary_paths/result.json');x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
