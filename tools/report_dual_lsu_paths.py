"""Collect routed LSU, registered completion and frontend timing without changing implementation."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 base=ROOT/'tools/report_dual_legacy_paths.py';s=base.read_text().replace("r'dual_legacy_[a-z_]+'","r'dual_lsu_[a-z_]+'");s=s.replace("'front_feedback':", "'lsu_request':' -to {soc/bus/ram_code/*/ADDRA* soc/bus/ram_data/*/ADDRA* soc/bus/ram_code/*/ADDRB* soc/bus/ram_data/*/ADDRB*}',\n 'lsu_feedback':' -from {soc/cpu/memory/p_* soc/cpu/memory/s_* soc/bus/*/CLK} -to {soc/cpu/fetch/head_* soc/cpu/operands/* soc/cpu/execute/*}',\n 'registered_load':' -from {soc/cpu/memory/load0_data*/CLK soc/cpu/memory/load1_data*/CLK soc/cpu/memory/load_tag*/CLK}',\n 'front_feedback':")
 # A candidate without result buses has no matching clocked load-data source.
 if sys.argv[-1] in ('dual_lsu_shared','dual_lsu_ports'):
  s=s.replace(" 'registered_load':' -from {soc/cpu/memory/load0_data*/CLK soc/cpu/memory/load1_data*/CLK soc/cpu/memory/load_tag*/CLK}',\n",'')
 ns={'__file__':str(base),'__name__':'lsu_paths'};exec(compile(s,str(base),'exec'),ns);ns['main']()
 p=ROOT/('simulation/results/load_bp_'+sys.argv[-1]+'/targeted_paths/result.json');x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
