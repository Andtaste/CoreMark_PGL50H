"""Include no-store throughput fixture without requiring artificial store activity."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 base=ROOT/'tools/check_dual_store_ack_soc.py';s=base.read_text().replace('posted_soc_verified','posted_soc_final')
 old="base=ROOT/'tools/check_dual_store_ack.py';s=base.read_text()";assert s.count(old)==1
 s=s.replace(old,old+".replace('posted_count==0 || posted_count!=drain_count','posted_count!=drain_count')")
 old="s=s.replace(' reg was_local;'";assert s.count(old)==1
 s=s.replace(old,"s=s.replace('  was_local=dut.bus.da_fire', '  if(dut.bus.da_fire && !dut.bus.db0 && !dut.bus.db1 && dut.bus.wa!==dut.bus.da) $fatal(1,\"Nonlocal request address is not registered MEM address\");\\n  was_local=dut.bus.da_fire')\n "+old)
 s=s.replace("'random_2026','prediction','soc_faults'","'random_2026','prediction','soc_faults','throughput'")
 sys.argv=[str(base),'--variant','dual_boundary_storemmio'];ns={'__file__':str(base),'__name__':'store_mmio_contract_v2'};exec(compile(s,str(base),'exec'),ns);ns['main']()
 p=ROOT/'simulation/results/load_bp_dual_boundary_storemmio/posted_soc_final/result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__));x['scope']+='; all accepted nonlocal requests use registered wa==da; throughput contains no local stores and correctly has zero posted/drain count'
 assert len(x['tests'])==6
 for t in x['tests']:
  if not t.startswith('throughput '):assert 'posted=0 ' not in t,t
 p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
