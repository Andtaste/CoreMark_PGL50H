"""Actual SoC fixtures, local response guarantee and fast-mode future tags."""
from pathlib import Path
import argparse,sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',default='dual_boundary_storeack');a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant)
 base=ROOT/'tools/check_dual_store_ack.py';s=base.read_text()
 s=s.replace("out=src/('posted_'+a.mode)","out=src/'posted_soc_verified'")
 s=s.replace("'random_2026','directed','soc_faults'","'random_2026','prediction','soc_faults'")
 s=s.replace(' reg was_local;',' reg was_local;reg[2:0] expect_f,expect_w;reg[3:0] expect_m;')
 s=s.replace('  was_local=dut.bus.da_fire', '  expect_f=dut.cpu.ex_tag;expect_w=dut.cpu.future_w_tag;expect_m=dut.cpu.m_next_tag;\n  was_local=dut.bus.da_fire')
 old='  if(was_local) begin local_count=local_count+1;'
 new='''  if((dut.cpu.f_valid || dut.cpu.f1_valid) && dut.cpu.f_tag!==expect_f) $fatal(1,"Fast SoC F tag contract");
  if(dut.cpu.commit && dut.cpu.w_tag!==expect_w) $fatal(1,"Fast SoC W tag contract");
  if(dut.cpu.m_valid && {dut.cpu.m_tag,dut.cpu.m_lane}!==expect_m) $fatal(1,"Fast SoC M tag contract");
  if(was_local) begin local_count=local_count+1;'''
 assert s.count(old)==1;s=s.replace(old,new)
 sys.argv=[str(base),'--variant',a.variant,'--mode','soc'];ns={'__file__':str(base),'__name__':'posted_soc_fixed'};exec(compile(s,str(base),'exec'),ns);ns['main']()
 p=src/'posted_soc_verified/result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__));x['scope']='Real SoC post-enabled local response guarantee and F/M/W future identities. directed.hex is an external core-bus fixture, not a SoC fixture; original misuse reproduced the same software failure on accepted baseline; retained as diagnostic. Directed core check remains included in standard63.';p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
