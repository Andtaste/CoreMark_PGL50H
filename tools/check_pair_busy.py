"""Check the redundant busy invariant on every cycle of parent lockstep tests."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'tools/check_auto_lockstep.py'
s=base.read_text()
needle="s=bench.read_text();start=s.index(' nc_core dut(')"
assert s.count(needle)==1
monitor='''
 reg[31:0] expected_pair_busy;integer busy_i;
 always @(negedge clk) if(rst_n) begin
  expected_pair_busy=0;
  for(busy_i=0;busy_i<8;busy_i=busy_i+1) if(dut.live[busy_i]) begin
   if(dut.destination[busy_i]!=0) expected_pair_busy[dut.destination[busy_i]]=1;
   if(dut.destination1[busy_i]!=0) expected_pair_busy[dut.destination1[busy_i]]=1;
  end
  if(dut.pair_busy !== expected_pair_busy) $fatal(1,"Busy invariant mismatch at cycle %0d",ticks);
  // Invalid fetch heads have uninitialized instruction fields; only a valid
  // second instruction can consume these pair-admission dependency signals.
  if(dut.id_valid && dut.id_second && {dut.pair_dep_c,dut.pair_dep_d} !== {dut.dep_c,dut.dep_d}) $fatal(1,"Pair dependency mismatch");
 end
'''
s=s.replace(needle,"s=bench.read_text().replace('endmodule',"+repr(monitor)+"+'\\nendmodule');start=s.index(' nc_core dut(')")
sys.argv=[str(base),'pair_busy','--reference','mul_early_products']
ns={'__file__':str(base),'__name__':'busy_lockstep'}
exec(compile(s,str(base),'exec'),ns);ns['main']()
p=ROOT/'simulation/results/autonomous_20261022/pair_busy/lockstep/result.json'
r=json.loads(p.read_text());assert r['status']=='PASS'
r['busy_invariant']='Every cycle: bitmap equals all live nonzero destinations, both side dependencies equal original ledger; original full core lockstep assertions retained.'
r.setdefault('input_sha256',{})[str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
p.write_text(json.dumps(r,indent=2)+'\n')
