"""Actual SoC published-bank identity, RAM CE, and existing tag contracts."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();base=ROOT/'tools/check_dual_store_simple_soc.py';s=base.read_text();needle="s=s.replace(' reg was_local;'";assert s.count(needle)==1
 mon='''  if(dut.ram_requests!==({2{dut.dv}} & {(dut.da>=32'h10000000 && dut.da<32'h10008000),dut.da<32'h00010000})) $fatal(1,"Published bank request identity");
  if(dut.bus.ram0_ce!==(dut.bus.da_fire && dut.bus.db0) || dut.bus.ram1_ce!==(dut.bus.da_fire && dut.bus.db1)) $fatal(1,"RAM CE differs from accepted original handshake");
  was_local=dut.bus.da_fire'''
 s=s.replace(needle,"s=s.replace('  was_local=dut.bus.da_fire', "+repr(mon)+")\n "+needle);ns={'__file__':str(base),'__name__':'bank_soc'};exec(compile(s,str(base),'exec'),ns);sys.argv=[str(base),'--variant',a.variant];ns['main']();p=ROOT/('simulation/results/load_bp_'+a.variant+'/posted_soc_final/result.json');x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();x['scope']+='; every-cycle published bank identity and physical RAM CE equality to original handshake';p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
