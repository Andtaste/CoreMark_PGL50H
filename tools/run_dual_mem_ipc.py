"""Bench-only decomposition of operand waits, MEM blocking and queued loads."""
from pathlib import Path
import sys,json,hashlib,re
import research_dual_issue as trial
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
MON=r'''
 integer mi_edge=0,mi_st=0,mi_mu=0,mi_ld=0,mi_other=0,mi_headld_st=0,mi_headld_mu=0,mi_headld_ld=0,mi_headld_other=0;
 integer mi_po=0,mi_so=0,mi_both=0,mi_waitld=0,mi_waitmu=0,mi_waitother=0,mi_full=0;
 integer mi_loads=0,mi_directld=0,mi_qloads=0,mi_delay=0,mi_delaymax=0,mi_d0=0,mi_d1=0,mi_d2=0,mi_d3=0,mi_d4=0;
 integer mi_issue_store=0,mi_store_alu=0,mi_store_load=0,mi_store_store=0,mi_store_mul=0;
 integer mi_exload[0:7];reg[1:0] mi_type[0:15];integer mi_i,mi_delta,mi_j;reg mi_p,mi_s,mi_hl,mi_hm,mi_ho;
 reg mi_last_store=0;
 always @(posedge clk) if(rst_n) begin
  mi_edge=mi_edge+1;
  if(CPU.issue) begin
   mi_type[{CPU.tail,1'b0}]=CPU.id_kind==4 ? 1 : CPU.id_kind==6 ? 2 : 0;
   mi_type[{CPU.tail,1'b1}]=CPU.id_side_kind==6 ? 2 : 0;
  end
  if(CPU.ex_fire && CPU.ex_packet[203:200]==4) mi_exload[CPU.ex_tag]=mi_edge;
  if(CPU.csr.stats.control && CPU.csr.stats.control_data[1]) begin
   mi_st=0;mi_mu=0;mi_ld=0;mi_other=0;mi_headld_st=0;mi_headld_mu=0;mi_headld_ld=0;mi_headld_other=0;
   mi_po=0;mi_so=0;mi_both=0;mi_waitld=0;mi_waitmu=0;mi_waitother=0;mi_full=0;
   mi_loads=0;mi_directld=0;mi_qloads=0;mi_delay=0;mi_delaymax=0;mi_d0=0;mi_d1=0;mi_d2=0;mi_d3=0;mi_d4=0;
   mi_last_store=0;mi_issue_store=0;mi_store_alu=0;mi_store_load=0;mi_store_store=0;mi_store_mul=0;
  end else if(!CPU.csr.stats.control && CPU.csr.stats.enabled) begin
   if(!CPU.memory_ready && !CPU.do_trap) begin
    if(CPU.memory.memory_access && CPU.memory.kind==5) mi_st=mi_st+1;
    else if(CPU.memory.multiply_access && !CPU.mul_query_ready) mi_mu=mi_mu+1;
    else if(CPU.memory.memory_access && CPU.memory.kind==4) mi_ld=mi_ld+1;
    else mi_other=mi_other+1;
    if(CPU.queued_valid && CPU.queued_packet[7:4]==4) begin
     if(CPU.memory.memory_access && CPU.memory.kind==5) mi_headld_st=mi_headld_st+1;
     else if(CPU.memory.multiply_access && !CPU.mul_query_ready) mi_headld_mu=mi_headld_mu+1;
     else if(CPU.memory.memory_access && CPU.memory.kind==4) mi_headld_ld=mi_headld_ld+1;
     else mi_headld_other=mi_headld_other+1;
    end
   end
   if(CPU.execute_valid && !CPU.mem_credit) mi_full=mi_full+1;
   if(CPU.ex_occupied && !CPU.ex_valid) begin
    mi_p=!CPU.operands.available_a[CPU.operands.rd] || !CPU.operands.available_b[CPU.operands.rd];
    mi_s=!CPU.operands.available_c[CPU.operands.rd] || !CPU.operands.available_d[CPU.operands.rd];
    if(mi_p && mi_s) mi_both=mi_both+1;else if(mi_p) mi_po=mi_po+1;else if(mi_s) mi_so=mi_so+1;
    mi_hl=0;mi_hm=0;mi_ho=0;
    for(mi_i=0;mi_i<4;mi_i=mi_i+1) begin
     case(mi_i)
      0:begin mi_j=CPU.operands.dep_a[CPU.operands.rd];mi_hl=mi_hl || (!CPU.operands.available_a[CPU.operands.rd] && mi_type[mi_j]==1);mi_hm=mi_hm || (!CPU.operands.available_a[CPU.operands.rd] && mi_type[mi_j]==2);end
      1:begin mi_j=CPU.operands.dep_b[CPU.operands.rd];mi_hl=mi_hl || (!CPU.operands.available_b[CPU.operands.rd] && mi_type[mi_j]==1);mi_hm=mi_hm || (!CPU.operands.available_b[CPU.operands.rd] && mi_type[mi_j]==2);end
      2:begin mi_j=CPU.operands.dep_c[CPU.operands.rd];mi_hl=mi_hl || (!CPU.operands.available_c[CPU.operands.rd] && mi_type[mi_j]==1);mi_hm=mi_hm || (!CPU.operands.available_c[CPU.operands.rd] && mi_type[mi_j]==2);end
      3:begin mi_j=CPU.operands.dep_d[CPU.operands.rd];mi_hl=mi_hl || (!CPU.operands.available_d[CPU.operands.rd] && mi_type[mi_j]==1);mi_hm=mi_hm || (!CPU.operands.available_d[CPU.operands.rd] && mi_type[mi_j]==2);end
     endcase
    end
    if(mi_hl) mi_waitld=mi_waitld+1;if(mi_hm) mi_waitmu=mi_waitmu+1;if(!mi_hl && !mi_hm) mi_waitother=mi_waitother+1;
   end
   if(CPU.memory.start) begin
    if(mi_last_store) begin
     case(CPU.mem_packet[7:4]) 4:mi_store_load=mi_store_load+1;5:mi_store_store=mi_store_store+1;6:mi_store_mul=mi_store_mul+1;default:mi_store_alu=mi_store_alu+1;endcase
    end
    mi_last_store=CPU.mem_packet[7:4]==5;
    if(mi_last_store) mi_issue_store=mi_issue_store+1;
    if(CPU.mem_packet[7:4]==4) begin
     mi_loads=mi_loads+1;if(CPU.direct_take) mi_directld=mi_directld+1;else mi_qloads=mi_qloads+1;
     mi_delta=mi_edge-mi_exload[CPU.mem_packet[279:277]];mi_delay=mi_delay+mi_delta;if(mi_delta>mi_delaymax) mi_delaymax=mi_delta;
     case(mi_delta) 0:mi_d0=mi_d0+1;1:mi_d1=mi_d1+1;2:mi_d2=mi_d2+1;3:mi_d3=mi_d3+1;default:mi_d4=mi_d4+1;endcase
    end
   end
  end
 end
 always @(negedge clk) if(check_secondary) begin
  $display("MEMIPC block_store=%0d block_mul=%0d block_load=%0d block_other=%0d head_load_store=%0d head_load_mul=%0d head_load_load=%0d head_load_other=%0d primary_only=%0d secondary_only=%0d both=%0d wait_load=%0d wait_mul=%0d wait_other=%0d ex_full=%0d",mi_st,mi_mu,mi_ld,mi_other,mi_headld_st,mi_headld_mu,mi_headld_ld,mi_headld_other,mi_po,mi_so,mi_both,mi_waitld,mi_waitmu,mi_waitother,mi_full);
  $display("MEMIPC_LOAD loads=%0d direct=%0d queued=%0d delay_sum=%0d delay_max=%0d d0=%0d d1=%0d d2=%0d d3=%0d d4plus=%0d",mi_loads,mi_directld,mi_qloads,mi_delay,mi_delaymax,mi_d0,mi_d1,mi_d2,mi_d3,mi_d4);
  $display("MEMIPC_STORE stores=%0d next_alu=%0d next_load=%0d next_store=%0d next_mul=%0d",mi_issue_store,mi_store_alu,mi_store_load,mi_store_store,mi_store_mul);
 end
'''
def main():
 variant=sys.argv[sys.argv.index('--variant')+1];phase=sys.argv[sys.argv.index('--phase')+1]
 prepare=trial.prepare_benches
 def benches(dest):
  result=prepare(dest)
  for p in result:p.write_text(p.read_text().replace('endmodule',MON.replace('CPU','dut.cpu' if p.name=='soc_tb.v' else 'dut')+'\nendmodule'))
  return result
 trial.prepare_benches=benches
 base=ROOT/'tools/run_dual_boundary_v3.py';ns={'__file__':str(base),'__name__':'mem_ipc_runner'};exec(compile(base.read_text(),str(base),'exec'),ns);ns['main']()
 src=ROOT/('simulation/results/load_bp_'+variant)
 for p in [src/phase/'result.json']+([src/'result.json'] if phase=='performance' else []):
  x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__))
  if phase in ('performance','validation'):
   t=(src/phase/'simulation.log').read_text(errors='replace')
   for field,marker in (('mem_ipc','MEMIPC'),('load_queue','MEMIPC_LOAD'),('store_followers','MEMIPC_STORE')):
    m=re.search(r'^'+marker+r' ([^\r\n]+)',t,re.M);assert m,marker;x[field]={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])}
   assert sum(x['mem_ipc'][k] for k in ('primary_only','secondary_only','both'))==int(x['metrics']['EX operand wait'].split()[0])
   assert sum(x['mem_ipc'][k] for k in ('block_store','block_mul','block_load','block_other'))==int(x['metrics']['MEM occupied cycles'].split()[0])
  p.write_text(json.dumps(x,indent=2)+'\n')
 print('MEM IPC observation PASS',variant,phase)
if __name__=='__main__':main()
