"""Check actual posted-enabled SoC tags and write publication every cycle."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();base=ROOT/'tools/check_dual_store_ack.py';s=base.read_text()
 s=s.replace("out=src/('posted_'+a.mode)","out=src/'posted_soc_final'").replace("'random_2026','directed','soc_faults'","'random_2026','prediction','soc_faults','throughput'").replace('posted_count==0 || posted_count!=drain_count','posted_count!=drain_count')
 s=s.replace(' reg was_local;',' reg was_local;reg[2:0] expect_f,expect_w;reg[3:0] expect_m;')
 old='  was_local=dut.bus.da_fire';assert s.count(old)==1;s=s.replace(old,'''  if(dut.bus.dwrite && (!dut.bus.dv || dut.bus.wa!==dut.bus.da)) $fatal(1,"Published write valid/address contract");
  if(dut.bus.da_fire && !dut.bus.db0 && !dut.bus.db1 && dut.bus.wa!==dut.bus.da) $fatal(1,"Nonlocal address contract");
  expect_f=dut.cpu.ex_tag;expect_w=dut.cpu.future_w_tag;expect_m=dut.cpu.m_next_tag;
  was_local=dut.bus.da_fire''')
 old='  if(was_local) begin local_count=local_count+1;';assert s.count(old)==1;s=s.replace(old,'''  if((dut.cpu.f_valid || dut.cpu.f1_valid) && dut.cpu.f_tag!==expect_f) $fatal(1,"F tag contract");
  if(dut.cpu.commit && dut.cpu.w_tag!==expect_w) $fatal(1,"W tag contract");
  if(dut.cpu.m_valid && {dut.cpu.m_tag,dut.cpu.m_lane}!==expect_m) $fatal(1,"M tag contract");
  if(was_local) begin local_count=local_count+1;''')
 sys.argv=[str(base),'--variant',a.variant,'--mode','soc'];ns={'__file__':str(base),'__name__':'simple_soc'};exec(compile(s,str(base),'exec'),ns);ns['main']();p=ROOT/('simulation/results/load_bp_'+a.variant+'/posted_soc_final/result.json');x=json.loads(p.read_text());assert len(x['tests'])==6
 for t in x['tests']:
  if not t.startswith('throughput '):assert 'posted=0 ' not in t,t
 x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();x['scope']='Real posted-enabled SoC: local accepted stores have no late errors; detached ack owner, F/M/W future tags, every-cycle published write implies valid and wa==da, accepted nonlocal address contract. Throughput has no store and allows zero activity.';p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
