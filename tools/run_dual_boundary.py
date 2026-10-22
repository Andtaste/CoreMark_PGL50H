"""Exercise uniform MEM boundary candidates with existing independent counters."""
from pathlib import Path
import json,sys,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 base=ROOT/'tools/run_dual_legacy.py';s=base.read_text().replace("variant.startswith('dual_legacy_')","variant.startswith('dual_boundary_')").replace("if variant!='dual_legacy_fifo':","if False:")
 ns={'__file__':str(base),'__name__':'boundary_runner'};exec(compile(s,str(base),'exec'),ns)
 trial=ns['trial'];prepare=trial.prepare_benches
 def benches(dest):
  paths=prepare(dest)
  mon='''
 integer br_mem=0,br_early=0,br_direct=0,br_spill=0,br_stall=0;
 always @(posedge clk) if(rst_n) begin
  if(CPU.csr.stats.control && CPU.csr.stats.control_data[1]) begin br_mem=0;br_early=0;br_direct=0;br_spill=0;br_stall=0;end
  else if(!CPU.csr.stats.control && CPU.csr.stats.enabled) begin
   if(CPU.memory.start && CPU.memory.input_memory) br_mem=br_mem+1;
   if(CPU.memory.early_request && CPU.d_req_ready) br_early=br_early+1;
   if(CPU.direct_take) br_direct=br_direct+1;
   if(CPU.execute_valid && CPU.mem_credit && !CPU.direct_take) br_spill=br_spill+1;
   if(CPU.memory.slot_valid && !CPU.memory.complete) br_stall=br_stall+1;
  end
  if(CPU.direct_take && !CPU.ex_fire) $fatal(1,"Direct MEM ownership without EX transfer");
  if(CPU.memory.early_request && (!CPU.memory.start || CPU.memory.old_request || CPU.memory.exception && CPU.memory.slot_valid)) $fatal(1,"Invalid early ownership");
 end
 always @(negedge clk) if(check_secondary) $display("BOUNDARY_WINDOW memory_groups=%0d early_accept=%0d direct=%0d spilled=%0d slot_stall=%0d",br_mem,br_early,br_direct,br_spill,br_stall);
'''
  for p in paths:
   cpu='dut.cpu' if p.name=='soc_tb.v' else 'dut';p.write_text(p.read_text().replace('endmodule',mon.replace('CPU',cpu)+'\nendmodule'))
  return paths
 trial.prepare_benches=benches;variant=sys.argv[sys.argv.index('--variant')+1];phase=sys.argv[sys.argv.index('--phase')+1];ns['main']()
 src=ROOT/('simulation/results/load_bp_'+variant)
 for p in [src/phase/'result.json']+([src/'result.json'] if phase=='performance' else []):
  x=json.loads(p.read_text(encoding='utf-8'));x['scope']='Uniform MEM ownership and empty spill-FIFO handoff; optional EX-edge local request; no raw RAM/EX bypass; not adopted'
  for n in (Path(__file__),ROOT/'tools/generate_dual_boundary.py'):x['input_sha256'][str(n.relative_to(ROOT))]=hashlib.sha256(n.read_bytes()).hexdigest()
  if phase in ('performance','validation'):
   import re
   t=(src/phase/'simulation.log').read_text();m=re.search(r'BOUNDARY_WINDOW ([^\r\n]+)',t);assert m;x['boundary']={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])}
  p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
