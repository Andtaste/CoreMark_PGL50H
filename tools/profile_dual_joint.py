"""Bench-only live producer, sliding adjacency, and slot mix assertions/counters."""
def instrument(s,cpu,variant):
 block=r'''
 integer j_cross=0,j_pop2=0,j_primary_branch=0,j_branch=0,j_mul=0,j_alu=0,j_wait_pair=0;
 integer j_dep=0,j_nosecond=0,j_class=0,j_misses=0,j_probes=0;
 reg[3:0] j_t;reg j_has;integer jn;reg j_found;
 always @(posedge clk) if(rst_n) begin
  if(CPU.ex_valid && CPU.ex_side[223] && (CPU.operands.wc[CPU.operands.rd] || CPU.operands.wd[CPU.operands.rd])) begin
   if(!CPU.operands.available_c[CPU.operands.rd] || !CPU.operands.available_d[CPU.operands.rd]) $fatal(1,"Execute with unavailable secondary source");
  end
  if(CPU.pair_issue && CPU.fetch.cross_window && CPU.fetch.metadata[CPU.fetch.following][31:0]!=CPU.id_pc+4) $fatal(1,"Cross-group adjacency");
  if(CPU.pair_issue && CPU.id_kind==1 && CPU.id_side_kind==1) $fatal(1,"Two branches admitted to one group");
  // Scoreboard youngest-producer check uses instruction order, not the DUT's
  // wrapped priority encoder. Lane1 follows lane0 within each live group.
  if(CPU.issue && CPU.pair_candidate) begin
   for(jn=0;jn<2;jn=jn+1) begin
    j_t=0;j_has=0;
    begin:check_age
     integer age,idx;reg[4:0] rs;
     rs=jn==0 ? CPU.rs1_1 : CPU.rs2_1;
     if((jn==0 ? CPU.id_pair_flags[5] : CPU.id_pair_flags[6]) && rs!=0) begin
      for(age=0;age<8;age=age+1) begin
       idx=(CPU.tail+age)&7;
       if(CPU.live[idx]) begin
        if(CPU.destination[idx]==rs) begin j_t={idx[2:0],1'b0};j_has=1;end
        if(CPU.destination1[idx]==rs) begin j_t={idx[2:0],1'b1};j_has=1;end
       end
      end
     end
    end
    if((jn==0 ? CPU.dep_c : CPU.dep_d)!==j_has || (j_has && (jn==0 ? CPU.tag_c : CPU.tag_d)!==j_t)) $fatal(1,"Secondary youngest producer mismatch");
   end
  end
  if(CPU.csr.stats.control && CPU.csr.stats.control_data[1]) begin
   j_cross=0;j_pop2=0;j_primary_branch=0;j_branch=0;j_mul=0;j_alu=0;j_wait_pair=0;
   j_dep=0;j_nosecond=0;j_class=0;j_misses=0;j_probes=0;
  end else if(!CPU.csr.stats.control && CPU.csr.stats.enabled) begin
   if(CPU.issue) begin
    if(!CPU.id_second) j_nosecond=j_nosecond+1;
    else if(CPU.second_dep) j_dep=j_dep+1;
    if(CPU.pair_issue) begin
     if(CPU.fetch.cross_window) j_cross=j_cross+1;
     if(CPU.dep_c || CPU.dep_d) j_wait_pair=j_wait_pair+1;
    end
   end
   if(CPU.fetch.pop_two_groups) j_pop2=j_pop2+1;
   if(CPU.commit1) begin
    if(CPU.w_kind==1) j_primary_branch=j_primary_branch+1;
    if(CPU.w1_branch) j_branch=j_branch+1;
    else if(CPU.w1_insn[6:0]==7'h33 && CPU.w1_insn[31:25]==1) j_mul=j_mul+1;
    else j_alu=j_alu+1;
   end
  end
 end
 always @(negedge clk) if(check_secondary) begin
  if(j_branch+j_mul+j_alu!=ref_secondary) $fatal(1,"Slot census mismatch");
  $display("JOINT_WINDOW cross=%0d pop2=%0d primary_branch=%0d branch=%0d mul=%0d alu=%0d dependent_pairs=%0d dependency_split=%0d no_second=%0d",j_cross,j_pop2,j_primary_branch,j_branch,j_mul,j_alu,j_wait_pair,j_dep,j_nosecond);
 end
'''
 return s.replace('endmodule',block.replace('CPU',cpu)+'\nendmodule')
