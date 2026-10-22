"""Existing independent regression harness plus observation-only opportunity counters."""
from pathlib import Path
import sys,json,re,hashlib
import research_dual_issue as trial
from run_dual_mul_tail_v2 import normalize
ROOT=Path(__file__).resolve().parents[1]
MON=r'''
 integer nx_alu=0,nx_load=0,nx_store=0,nx_mul=0,nx_branch=0,nx_other=0,nx_groups=0,nx_kind=0;
 integer nx_pre=0,nx_saved=0,nx_posthold=0,nx_return=0,nx_returnex=0;
 integer nx_last=-1,nx_recovery=0,nx_recovered=0,nx_edge=0;reg[2:0] nx_prevtag;
 reg nx_sidewait;reg nx_exp_m;
 always @(posedge clk) if(rst_n) begin
  nx_edge=nx_edge+1;
  NEXT_VALID_CAPTURE
  if(CPU.csr.stats.control && CPU.csr.stats.control_data[1]) begin
   nx_alu=0;nx_load=0;nx_store=0;nx_mul=0;nx_branch=0;nx_other=0;nx_groups=0;
   nx_pre=0;nx_saved=0;nx_posthold=0;nx_return=0;nx_returnex=0;
   nx_last=-1;nx_recovery=0;nx_recovered=0;
  end else if(!CPU.csr.stats.control && CPU.csr.stats.enabled) begin
   nx_sidewait=CPU.ex_occupied && !CPU.ex_valid && CPU.operands.available_a[CPU.operands.rd] && CPU.operands.available_b[CPU.operands.rd];
   if(nx_sidewait) begin
    nx_kind=CPU.ex_packet[203:200];
    case(nx_kind) 0:nx_alu=nx_alu+1;4:nx_load=nx_load+1;5:nx_store=nx_store+1;6:nx_mul=nx_mul+1;1,2,3:nx_branch=nx_branch+1;default:nx_other=nx_other+1;endcase
   end
   SPECIAL_COUNTERS
   if(CPU.branch_event) nx_last=nx_edge;
   if(nx_last>=0 && CPU.ex_fire && nx_edge>nx_last && !CPU.redirect) begin nx_recovered=nx_recovered+1;nx_recovery=nx_recovery+nx_edge-nx_last;nx_last=-1;end
  end
  NEXT_VALID_CHECK
 end
 always @(negedge clk) if(check_secondary) $display("NEXT_WINDOW sidewait_alu=%0d sidewait_load=%0d sidewait_store=%0d sidewait_mul=%0d sidewait_branch=%0d sidewait_other=%0d early_mul=%0d held_response=%0d held_posted=%0d load_return=%0d concurrent_return_ex=%0d recovery_samples=%0d recovery_sum=%0d",nx_alu,nx_load,nx_store,nx_mul,nx_branch,nx_other,nx_pre,nx_saved,nx_posthold,nx_return,nx_returnex,nx_recovered,nx_recovery);
'''
def main():
 variant=sys.argv[sys.argv.index('--variant')+1];phase=sys.argv[sys.argv.index('--phase')+1];kind=variant.rsplit('_',1)[1]
 prep=trial.prepare_benches
 def benches(dest):
  paths=prep(dest)
  for p in paths:
   cpu='dut.cpu' if p.name=='soc_tb.v' else 'dut';s=normalize(p.read_text(),cpu);mon=MON
   special=''
   if kind=='mpre':special+='if(CPU.primary_mul_early && !CPU.ex_fire) nx_pre=nx_pre+1;\n'
   if kind=='pairmul':special+='if(CPU.memory.raw_response && !CPU.memory.complete) nx_saved=nx_saved+1;if(CPU.memory.posted_fire && !CPU.memory.complete) nx_posthold=nx_posthold+1;\n'
   if kind in ('loadwake','wordwake'):special+='if(CPU.r_valid) begin nx_return=nx_return+1;if(CPU.ex_fire) nx_returnex=nx_returnex+1;end\n'
   mon=mon.replace('SPECIAL_COUNTERS',special).replace('NEXT_VALID_CAPTURE','nx_exp_m=CPU.m_next_valid;' if kind=='mqual' else '').replace('NEXT_VALID_CHECK','#1;if(CPU.m_valid!==nx_exp_m) $fatal(1,"M next-valid protocol");' if kind=='mqual' else '')
   p.write_text(s.replace('endmodule',mon.replace('CPU',cpu)+'\nendmodule'))
  return paths
 trial.prepare_benches=benches
 import run_dual_mem_ipc
 run_dual_mem_ipc.main()
 src=ROOT/('simulation/results/load_bp_'+variant)
 for p in [src/phase/'result.json']+([src/'result.json'] if phase=='performance' else []):
  x=json.loads(p.read_text());x['scope']='Independent '+kind+' trial on accepted storewrite; NOT ADOPTED';x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
  if phase in ('performance','validation'):
   m=re.search(r'^NEXT_WINDOW ([^\r\n]+)',(src/phase/'simulation.log').read_text(errors='replace'),re.M);assert m;x['next_trial']={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])}
  p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
