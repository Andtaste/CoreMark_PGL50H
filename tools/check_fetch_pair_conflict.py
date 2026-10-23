"""Compare cached pair legality against original ID decode on valid fetch pairs."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'tools/check_auto_lockstep.py';s=base.read_text()
needle="s=bench.read_text();start=s.index(' nc_core dut(')";assert s.count(needle)==1
monitor='''
 wire expected_pair_conflict=dut.id_pair_flags[2] && dut.rd!=0 &&
  ((dut.id_pair_flags[5] && dut.rd==dut.rs1_1) ||
   (dut.id_pair_flags[6] && dut.rd==dut.rs2_1) ||
   (dut.id_pair_flags[7] && dut.rd==dut.rd1));
 always @(negedge clk) if(rst_n && dut.id_valid && dut.id_second) begin
  if(dut.id_pair_conflict !== expected_pair_conflict) $fatal(1,"Cached pair conflict mismatch at %0d",ticks);
 end
'''
s=s.replace(needle,"s=bench.read_text().replace('endmodule',"+repr(monitor)+"+'\\nendmodule');start=s.index(' nc_core dut(')")
sys.argv=[str(base),'fetch_pair_conflict','--reference','mul_early_products']
ns={'__file__':str(base),'__name__':'fetch_conflict_lockstep'}
exec(compile(s,str(base),'exec'),ns);ns['main']()
p=ROOT/'simulation/results/autonomous_20261022/fetch_pair_conflict/lockstep/result.json'
r=json.loads(p.read_text());assert r['status']=='PASS'
r['additional_invariant']='Every valid cached pair: registered conflict equals original decoded intra-pair RAW/WAW expression; original full core lockstep checks retained.'
r.setdefault('input_sha256',{})[str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
p.write_text(json.dumps(r,indent=2)+'\n')
