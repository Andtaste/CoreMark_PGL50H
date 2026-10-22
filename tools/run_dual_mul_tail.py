"""Observe terminal MUL handoff and disjoint pairing rejection categories."""
from pathlib import Path
import hashlib,json,re,sys
import research_dual_issue as trial
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
MON=r'''
 integer mt_lo=0,mt_hi=0,mt_terminal=0,mt_early=0,mt_otherwait=0,mt_latency=0,mt_maxlat=0,mt_done=0,mt_trace=0;
 integer mt_edge=0,mt_start[0:7],mt_delta;
 wire mt_l=CPU.multiply.low_done && CPU.multiply.tag1==CPU.mul_query_tag;
 wire mt_h=CPU.multiply.high_done && CPU.multiply.tag2==CPU.mul_query_tag;
 integer pr_groups=0,pr_pair=0,pr_no=0,pr_primary=0,pr_side=0,pr_restrict=0,pr_pred=0,pr_raw=0,pr_waw=0,pr_other=0;
 integer pr_no_taken=0,pr_no_empty=0,pr_no_nonseq=0,pr_no_fault=0,pr_no_other=0;
 integer pc_alu=0,pc_branch=0,pc_mul=0,pc_load=0,pc_store=0,pc_jump=0,pc_other=0,pc_raw=0,pc_waw=0,pc_lsu=0,pc_mulconflict=0;
 integer pe_branch_mem=0,pe_branch_mul=0,pe_mul_mem=0,pe_branch_mem_ready=0,pe_branch_mul_ready=0,pe_mul_mem_ready=0;
 wire pr_raw_exact=CPU.id_pair_flags[2] && CPU.rd!=0 && ((CPU.id_pair_flags[5] && CPU.rd==CPU.rs1_1) || (CPU.id_pair_flags[6] && CPU.rd==CPU.rs2_1));
 wire pr_waw_exact=CPU.id_pair_flags[2] && CPU.id_pair_flags[7] && CPU.rd!=0 && CPU.rd==CPU.rd1;
 wire pc_raw_full=CPU.id_wr && CPU.rd!=0 && ((CPU.id1_use1 && CPU.rd==CPU.rs1_1) || (CPU.id1_use2 && CPU.rd==CPU.rs2_1));
 wire pc_waw_full=CPU.id_wr && CPU.id1_wr && CPU.rd!=0 && CPU.rd==CPU.rd1;
 wire pc_c_ready=!CPU.dep_c || (CPU.f_valid && CPU.tag_c=={CPU.f_tag,1'b0}) || (CPU.f1_valid && CPU.tag_c=={CPU.f1_tag,1'b1}) || (CPU.m_valid && CPU.tag_c=={CPU.m_tag,CPU.m_lane}) || (CPU.commit && CPU.w_wr && CPU.w_rd!=0 && CPU.tag_c=={CPU.w_tag,1'b0}) || (CPU.commit1 && CPU.w1_rd!=0 && CPU.tag_c=={CPU.w_tag,1'b1});
 wire pc_d_ready=!CPU.dep_d || (CPU.f_valid && CPU.tag_d=={CPU.f_tag,1'b0}) || (CPU.f1_valid && CPU.tag_d=={CPU.f1_tag,1'b1}) || (CPU.m_valid && CPU.tag_d=={CPU.m_tag,CPU.m_lane}) || (CPU.commit && CPU.w_wr && CPU.w_rd!=0 && CPU.tag_d=={CPU.w_tag,1'b0}) || (CPU.commit1 && CPU.w1_rd!=0 && CPU.tag_d=={CPU.w_tag,1'b1});
 always @(posedge clk) if(rst_n) begin
  mt_edge=mt_edge+1;
  if(CPU.mul_accept) mt_start[CPU.ex_tag]=mt_edge;
  if(CPU.csr.stats.control && CPU.csr.stats.control_data[1]) begin
   mt_lo=0;mt_hi=0;mt_terminal=0;mt_early=0;mt_otherwait=0;mt_latency=0;mt_maxlat=0;mt_done=0;mt_trace=0;
   pr_groups=0;pr_pair=0;pr_no=0;pr_primary=0;pr_side=0;pr_restrict=0;pr_pred=0;pr_raw=0;pr_waw=0;pr_other=0;
   pr_no_taken=0;pr_no_empty=0;pr_no_nonseq=0;pr_no_fault=0;pr_no_other=0;
   pc_alu=0;pc_branch=0;pc_mul=0;pc_load=0;pc_store=0;pc_jump=0;pc_other=0;pc_raw=0;pc_waw=0;pc_lsu=0;pc_mulconflict=0;
   pe_branch_mem=0;pe_branch_mul=0;pe_mul_mem=0;pe_branch_mem_ready=0;pe_branch_mul_ready=0;pe_mul_mem_ready=0;
  end else if(!CPU.csr.stats.control && CPU.csr.stats.enabled) begin
   if(CPU.mul_accept) begin if(CPU.mul_op==0) mt_lo=mt_lo+1;else mt_hi=mt_hi+1;end
   if(CPU.memory.slot_valid && CPU.memory.multiply_access && (mt_l || mt_h) && !CPU.multiply.available[CPU.mul_query_tag]) mt_terminal=mt_terminal+1;
   if(!CPU.memory_ready && !CPU.do_trap && CPU.memory.multiply_access && !CPU.mul_query_ready && !(mt_l || mt_h)) mt_otherwait=mt_otherwait+1;
   if(CPU.mul_consume) begin
    mt_done=mt_done+1;mt_delta=mt_edge-mt_start[CPU.mul_query_tag];mt_latency=mt_latency+mt_delta;if(mt_delta>mt_maxlat) mt_maxlat=mt_delta;
    if((mt_l || mt_h) && !CPU.multiply.available[CPU.mul_query_tag]) mt_early=mt_early+1;
    if(mt_trace<16) begin $display("MUL_HANDOFF edge=%0d tag=%0d latency=%0d table=%0d low=%0d high=%0d",mt_edge,CPU.mul_query_tag,mt_delta,CPU.multiply.available[CPU.mul_query_tag],mt_l,mt_h);mt_trace=mt_trace+1;end
   end
   if(CPU.issue) begin
    pr_groups=pr_groups+1;
    if(CPU.pair_issue) pr_pair=pr_pair+1;
    else if(!CPU.id_second) begin
     pr_no=pr_no+1;
     if(CPU.id_prediction[30]) pr_no_taken=pr_no_taken+1;
     else if(CPU.fetch.count<2) pr_no_empty=pr_no_empty+1;
     else if(!CPU.fetch.head_1[32]) pr_no_nonseq=pr_no_nonseq+1;
     else if(CPU.fetch.head_1[33]) pr_no_fault=pr_no_fault+1;
     else pr_no_other=pr_no_other+1;
    end else if(!CPU.id_pair_flags[4]) pr_primary=pr_primary+1;
    else if(!CPU.id_pair_flags[8] && !CPU.id_pair_flags[9]) pr_side=pr_side+1;
    else if(!CPU.id_pair_flags[8] && !CPU.id_pair_flags[3]) pr_restrict=pr_restrict+1;
    else if(!(!CPU.id_prediction[30] && ((CPU.id_pair_flags[8] && !CPU.id_prediction1[31]) || (CPU.extended_pair && (CPU.id_insn1[6] || !CPU.id_prediction1[31]))))) pr_pred=pr_pred+1;
    else if(pr_raw_exact) pr_raw=pr_raw+1;
    else if(pr_waw_exact) pr_waw=pr_waw+1;
    else pr_other=pr_other+1;
    if(CPU.id_second) begin
     case(CPU.id1_kind) 0:pc_alu=pc_alu+1;1:pc_branch=pc_branch+1;4:pc_load=pc_load+1;5:pc_store=pc_store+1;6:if(!CPU.id_insn1[14]) pc_mul=pc_mul+1;else pc_other=pc_other+1;2,3:pc_jump=pc_jump+1;default:pc_other=pc_other+1;endcase
     if(pc_raw_full) pc_raw=pc_raw+1;if(pc_waw_full) pc_waw=pc_waw+1;
     if((CPU.id_kind==4 || CPU.id_kind==5) && (CPU.id1_kind==4 || CPU.id1_kind==5)) pc_lsu=pc_lsu+1;
     if(CPU.id_kind==6 && !CPU.id_insn[14] && CPU.id1_kind==6 && !CPU.id_insn1[14]) pc_mulconflict=pc_mulconflict+1;
     if(!CPU.id_fault && !CPU.id_illegal && !CPU.id1_illegal && !pc_raw_full && !pc_waw_full && !CPU.id_prediction[31] && CPU.id_pair_flags[9]) begin
      if(CPU.id1_kind==1 && (CPU.id_kind==4 || CPU.id_kind==5)) begin pe_branch_mem=pe_branch_mem+1;if(pc_c_ready && pc_d_ready) pe_branch_mem_ready=pe_branch_mem_ready+1;end
      if(CPU.id1_kind==1 && CPU.id_kind==6 && !CPU.id_insn[14]) begin pe_branch_mul=pe_branch_mul+1;if(pc_c_ready && pc_d_ready) pe_branch_mul_ready=pe_branch_mul_ready+1;end
      if(CPU.id1_kind==6 && !CPU.id_insn1[14] && !CPU.id_prediction1[31] && (CPU.id_kind==4 || CPU.id_kind==5)) begin pe_mul_mem=pe_mul_mem+1;if(pc_c_ready && pc_d_ready) pe_mul_mem_ready=pe_mul_mem_ready+1;end
     end
    end
   end
  end
 end
 always @(negedge clk) if(check_secondary) begin
  if(pr_groups!=pr_pair+pr_no+pr_primary+pr_side+pr_restrict+pr_pred+pr_raw+pr_waw+pr_other || pr_other!=0) $fatal(1,"Pair rejection census partition");
  if(pr_no!=pr_no_taken+pr_no_empty+pr_no_nonseq+pr_no_fault+pr_no_other || pr_no_other!=0) $fatal(1,"Second supply census partition");
  if(pc_alu+pc_branch+pc_mul+pc_load+pc_store+pc_jump+pc_other!=pr_groups-pr_no) $fatal(1,"Side type census partition");
  $display("MUL_TAIL low=%0d high=%0d terminal_head=%0d early_consume=%0d other_wait=%0d latency_sum=%0d max_latency=%0d consumed=%0d",mt_lo,mt_hi,mt_terminal,mt_early,mt_otherwait,mt_latency,mt_maxlat,mt_done);
  $display("PAIR_REJECT groups=%0d paired=%0d no_second=%0d primary_type=%0d secondary_type=%0d restricted_primary=%0d prediction=%0d raw=%0d waw=%0d other=%0d",pr_groups,pr_pair,pr_no,pr_primary,pr_side,pr_restrict,pr_pred,pr_raw,pr_waw,pr_other);
  $display("PAIR_SUPPLY taken=%0d empty=%0d nonsequential=%0d fault=%0d other=%0d",pr_no_taken,pr_no_empty,pr_no_nonseq,pr_no_fault,pr_no_other);
  $display("PAIR_CENSUS alu=%0d branch=%0d mul=%0d load=%0d store=%0d jump=%0d other=%0d raw_overlap=%0d waw_overlap=%0d lsu_conflict_overlap=%0d mul_conflict_overlap=%0d",pc_alu,pc_branch,pc_mul,pc_load,pc_store,pc_jump,pc_other,pc_raw,pc_waw,pc_lsu,pc_mulconflict);
  $display("PAIR_EXPAND branch_on_mem=%0d branch_on_mul=%0d mul_on_mem=%0d branch_on_mem_ready=%0d branch_on_mul_ready=%0d mul_on_mem_ready=%0d",pe_branch_mem,pe_branch_mul,pe_mul_mem,pe_branch_mem_ready,pe_branch_mul_ready,pe_mul_mem_ready);
 end
'''
def main():
 variant=sys.argv[sys.argv.index('--variant')+1];phase=sys.argv[sys.argv.index('--phase')+1];prepare=trial.prepare_benches
 def benches(dest):
  result=prepare(dest)
  for p in result:p.write_text(p.read_text().replace('endmodule',MON.replace('CPU','dut.cpu' if p.name=='soc_tb.v' else 'dut')+'\nendmodule'))
  return result
 trial.prepare_benches=benches;base=ROOT/'tools/run_dual_mem_ipc.py';ns={'__file__':str(base),'__name__':'mul_tail_runner'};exec(compile(base.read_text(),str(base),'exec'),ns);ns['main']();src=ROOT/('simulation/results/load_bp_'+variant)
 for p in [src/phase/'result.json']+([src/'result.json'] if phase=='performance' else []):
  x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__))
  if phase in ('performance','validation'):
   t=(src/phase/'simulation.log').read_text(errors='replace')
   for field,marker in (('mul_tail','MUL_TAIL'),('pair_reject','PAIR_REJECT'),('pair_supply','PAIR_SUPPLY'),('pair_census','PAIR_CENSUS'),('pair_expand','PAIR_EXPAND')):
    m=re.search(r'^'+marker+r' ([^\r\n]+)',t,re.M);assert m,marker;x[field]={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])}
   assert x['pair_reject']['groups']==x['dual']['groups_issued'] and x['pair_reject']['paired']==x['dual']['pairs_issued']
  p.write_text(json.dumps(x,indent=2)+'\n')
 print('MUL tail and pair census PASS',variant,phase)
if __name__=='__main__':main()
