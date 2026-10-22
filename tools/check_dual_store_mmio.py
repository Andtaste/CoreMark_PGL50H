"""Strengthen the real-SoC registered nonlocal-address contract."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 base=ROOT/'tools/check_dual_store_ack_soc.py';s=base.read_text()
 old="s=s.replace(' reg was_local;'"
 assert s.count(old)==1
 s=s.replace(old,"s=s.replace('  was_local=dut.bus.da_fire', '  if(dut.bus.da_fire && !dut.bus.db0 && !dut.bus.db1 && dut.bus.wa!==dut.bus.da) $fatal(1,\"Nonlocal request address is not registered MEM address\");\\n  was_local=dut.bus.da_fire')\n "+old)
 # Run all standard supported SoC fixtures, including MMIO faults and loops.
 s=s.replace("'random_2026','prediction','soc_faults'", "'random_2026','prediction','soc_faults','throughput'") if "'random_2026','prediction','soc_faults'" in s else s
 sys.argv=[str(base),'--variant','dual_boundary_storemmio'];ns={'__file__':str(base),'__name__':'store_mmio_contract'};exec(compile(s,str(base),'exec'),ns);ns['main']()
 p=ROOT/'simulation/results/load_bp_dual_boundary_storemmio/posted_soc_verified/result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__));x['scope']+='; every accepted nonlocal request satisfies wa==da, MMIO decoder uses registered wa';p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
