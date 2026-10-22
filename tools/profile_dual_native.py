"""Simulation-only disjoint pairing rejection counters and WB opportunity audit."""
def instrument(s,cpu,cross=False):
 block=r'''
 integer ap_total=0,ap_no_second=0,ap_primary=0,ap_secondary=0,ap_prediction=0;
 integer ap_raw=0,ap_waw=0,ap_dependency=0,ap_pair=0,ap_wb_opportunity=0,ap_cross=0;
 integer an;reg any_secondary_dep,remaining_secondary_dep;reg statically_pairable;
 always @* begin
  any_secondary_dep=0;remaining_secondary_dep=0;
  for(an=0;an<8;an=an+1) if(CPU.live[an]) begin
   if((CPU.id_pair_flags[5] && CPU.rs1_1!=0 && CPU.destination[an]==CPU.rs1_1) ||
      (CPU.id_pair_flags[6] && CPU.rs2_1!=0 && CPU.destination[an]==CPU.rs2_1)) begin
    any_secondary_dep=1;
    if(!(CPU.commit && CPU.w_wr && CPU.w_tag==an[2:0])) remaining_secondary_dep=1;
   end
   if((CPU.id_pair_flags[5] && CPU.rs1_1!=0 && CPU.destination1[an]==CPU.rs1_1) ||
      (CPU.id_pair_flags[6] && CPU.rs2_1!=0 && CPU.destination1[an]==CPU.rs2_1)) begin
    any_secondary_dep=1;
    if(!(CPU.commit1 && CPU.w_tag==an[2:0])) remaining_secondary_dep=1;
   end
  end
 end
 always @(posedge clk) if(rst_n) begin
  if(CPU.csr.stats.control && CPU.csr.stats.control_data[1]) begin
   ap_total=0;ap_no_second=0;ap_primary=0;ap_secondary=0;ap_prediction=0;
   ap_raw=0;ap_waw=0;ap_dependency=0;ap_pair=0;ap_wb_opportunity=0;ap_cross=0;
  end else if(!CPU.csr.stats.control && CPU.csr.stats.enabled && CPU.issue) begin
   ap_total=ap_total+1;statically_pairable=0;
   if(!CPU.id_second) ap_no_second=ap_no_second+1;
   else if(CPU.id_fault || !CPU.id_pair_flags[4]) ap_primary=ap_primary+1;
   else if(!CPU.id_pair_flags[8]) ap_secondary=ap_secondary+1;
   else if(CPU.id_prediction[30] || CPU.id_prediction1[31]) ap_prediction=ap_prediction+1;
   else if(CPU.id_pair_flags[2] && CPU.rd!=0 &&
           ((CPU.id_pair_flags[5] && CPU.rd==CPU.rs1_1) || (CPU.id_pair_flags[6] && CPU.rd==CPU.rs2_1))) ap_raw=ap_raw+1;
   else if(CPU.id_pair_flags[2] && CPU.rd!=0 && CPU.rd==CPU.rd1) ap_waw=ap_waw+1;
   else begin
    statically_pairable=1;
    if(CPU.second_dep) ap_dependency=ap_dependency+1;
    else ap_pair=ap_pair+1;
   end
   if(statically_pairable && any_secondary_dep && !remaining_secondary_dep) ap_wb_opportunity=ap_wb_opportunity+1;
   CROSS_COUNTER
  end
  CROSS_ASSERTION
 end
 always @(negedge clk) if(check_secondary) begin
  if(ap_total!=ap_no_second+ap_primary+ap_secondary+ap_prediction+ap_raw+ap_waw+ap_dependency+ap_pair)
   $fatal(1,"Admission reasons do not partition all issued groups");
  if(ap_total!=win_issued || ap_pair!=win_pairs) $fatal(1,"Admission/reference count mismatch");
  $display("ADMISSION_WINDOW total=%0d no_second=%0d primary=%0d secondary=%0d prediction=%0d raw=%0d waw=%0d dependency=%0d paired=%0d wb_only_opportunity=%0d cross_pairs=%0d",
   ap_total,ap_no_second,ap_primary,ap_secondary,ap_prediction,ap_raw,ap_waw,ap_dependency,ap_pair,ap_wb_opportunity,ap_cross);
 end
'''
 block=block.replace('CROSS_COUNTER','if(CPU.pair_issue && CPU.id_pc[2]) ap_cross=ap_cross+1;' if cross else '')
 block=block.replace('CROSS_ASSERTION',r'''if(CPU.fetch.valid && CPU.id_second && CPU.fetch.head_1[105:74]!=CPU.id_pc+32'd4)
   $fatal(1,"Nonsequential following-group window pc=%h following=%h",CPU.id_pc,CPU.fetch.head_1[105:74]);''' if cross else '')
 return s.replace('endmodule',block.replace('CPU',cpu)+'\nendmodule')
