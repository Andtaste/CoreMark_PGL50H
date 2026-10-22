"""Bench-only type, dependency/resource overlap, and frontend provenance counters."""
def instrument(s,cpu,baseline=False):
 if baseline:
  from profile_dual_admit import instrument as old
  s=old(s,cpu)
 block=r'''
 function integer type_category;
  input[3:0] kind;input[31:0] insn;
  begin case(kind)
   1:type_category=0;2:type_category=1;3:type_category=2;
   6:type_category=insn[14] ? 4 : 3;
   4:type_category=5;5:type_category=6;7:type_category=7;default:type_category=8;
  endcase end
 endfunction
 integer type_count[0:8],type_raw[0:8],type_waw[0:8],type_old[0:8],type_resource[0:8];
 integer type_pred[0:8],type_align[0:8],type_not_plain[0:8],type_clean[0:8],type_clean_plain[0:8];
 integer no_second_reason[0:4],cross_count[0:8],cross_clean[0:8],cross_plain=0;
 integer ti,tn,tc;reg traw,twaw,told,tresource,tpred,talign,tplain;
 reg[2:0] front_origin[0:3];reg[2:0] head_origin=0;
 wire[2:0] incoming_origin=CPU.fetch.flight_two ? 3'd0 : CPU.fetch.flight_pc[2] ? 3'd1 : CPU.fetch.flight_prediction[30] ? 3'd2 : 3'd4;
 always @(posedge clk) if(!rst_n || CPU.redirect) head_origin<=0;
 else begin
  if(CPU.fetch.push) front_origin[CPU.fetch.wr]<=incoming_origin;
  if(CPU.fetch.consume) begin
   if(CPU.id_second && !CPU.pair_issue) head_origin<=3;
   else if(CPU.fetch.count>1) head_origin<=front_origin[CPU.fetch.following];
   else head_origin<=CPU.fetch.push ? incoming_origin : 3'd0;
  end else if(CPU.fetch.push && CPU.fetch.count==0) head_origin<=incoming_origin;
 end
 wire[31:0] cross_insn=CPU.fetch.instructions[CPU.fetch.following][31:0];
 wire[33:0] cross_meta=CPU.fetch.metadata[CPU.fetch.following];
 wire[31:0] cross_prediction=CPU.fetch.predictions[CPU.fetch.following][31:0];
 wire[3:0] cross_kind;wire cross_u1,cross_u2,cross_wr,cross_serial,cross_illegal;
 wire[4:0] cross_rs1,cross_rs2,cross_rd;
 nc_decode cross_decode(.insn(cross_insn),.kind(cross_kind),.imm(),.use1(cross_u1),.use2(cross_u2),
  .write_rd(cross_wr),.serial(cross_serial),.illegal(cross_illegal),.control(),.rs1(cross_rs1),.rs2(cross_rs2),.rd(cross_rd),.csr_exists(1'b0),.csr_writable(1'b0));
 initial begin
  for(ti=0;ti<9;ti=ti+1) begin
   type_count[ti]=0;type_raw[ti]=0;type_waw[ti]=0;type_old[ti]=0;type_resource[ti]=0;
   type_pred[ti]=0;type_align[ti]=0;type_not_plain[ti]=0;type_clean[ti]=0;type_clean_plain[ti]=0;cross_count[ti]=0;cross_clean[ti]=0;
  end
  for(ti=0;ti<5;ti=ti+1) no_second_reason[ti]=0;
 end
 always @(posedge clk) if(rst_n) begin
  if(CPU.csr.stats.control && CPU.csr.stats.control_data[1]) begin
   for(ti=0;ti<9;ti=ti+1) begin
    type_count[ti]=0;type_raw[ti]=0;type_waw[ti]=0;type_old[ti]=0;type_resource[ti]=0;
    type_pred[ti]=0;type_align[ti]=0;type_not_plain[ti]=0;type_clean[ti]=0;type_clean_plain[ti]=0;cross_count[ti]=0;cross_clean[ti]=0;
   end
   for(ti=0;ti<5;ti=ti+1) no_second_reason[ti]=0;cross_plain=0;
  end else if(!CPU.csr.stats.control && CPU.csr.stats.enabled && CPU.issue) begin
   if(!CPU.id_second) begin
    no_second_reason[head_origin]=no_second_reason[head_origin]+1;
    // Observed already-buffered following group only; this is opportunity,
    // not a prediction of cycle savings or permission to cross a branch.
    if(CPU.fetch.count>1 && !CPU.id_fault && cross_meta[31:0]==CPU.id_pc+4 && !cross_meta[32] && !CPU.id_prediction[30] && CPU.id_pair_flags[4]) begin
     tc=type_category(cross_kind,cross_insn);cross_count[tc]=cross_count[tc]+1;
     told=0;
     for(tn=0;tn<8;tn=tn+1) if(CPU.live[tn]) begin
      if((cross_u1 && cross_rs1!=0 && (CPU.destination[tn]==cross_rs1 || CPU.destination1[tn]==cross_rs1)) ||
         (cross_u2 && cross_rs2!=0 && (CPU.destination[tn]==cross_rs2 || CPU.destination1[tn]==cross_rs2))) told=1;
     end
     traw=CPU.id_wr && CPU.rd!=0 && ((cross_u1 && CPU.rd==cross_rs1)||(cross_u2 && CPU.rd==cross_rs2));
     twaw=CPU.id_wr && cross_wr && CPU.rd!=0 && CPU.rd==cross_rd;
     if(!told && !traw && !twaw && !cross_prediction[31] && !cross_illegal) begin
      cross_clean[tc]=cross_clean[tc]+1;
      if(cross_kind==0) cross_plain=cross_plain+1;
     end
    end
   end
   if(CPU.id_second && !CPU.id_fault && CPU.id_pair_flags[4] && !CPU.id_pair_flags[8]) begin
    tc=type_category(CPU.id1_kind,CPU.id_insn1);type_count[tc]=type_count[tc]+1;
    traw=CPU.id_wr && CPU.rd!=0 && ((CPU.id1_use1 && CPU.rd==CPU.rs1_1)||(CPU.id1_use2 && CPU.rd==CPU.rs2_1));
    twaw=CPU.id_wr && CPU.id1_wr && CPU.rd!=0 && CPU.rd==CPU.rd1;
    told=0;
    for(tn=0;tn<8;tn=tn+1) if(CPU.live[tn]) begin
     if((CPU.id1_use1 && CPU.rs1_1!=0 && (CPU.destination[tn]==CPU.rs1_1 || CPU.destination1[tn]==CPU.rs1_1)) ||
        (CPU.id1_use2 && CPU.rs2_1!=0 && (CPU.destination[tn]==CPU.rs2_1 || CPU.destination1[tn]==CPU.rs2_1))) told=1;
    end
    tresource=((CPU.id_kind==4 || CPU.id_kind==5) && (CPU.id1_kind==4 || CPU.id1_kind==5)) ||
      (CPU.id_kind==6 && CPU.id1_kind==6);
    tpred=CPU.id_prediction[30] || CPU.id_prediction1[31];
    talign=CPU.id1_kind==1 && CPU.id_insn1[8];
    tplain=CPU.id_pair_flags[3] && !CPU.id_prediction[31];
    if(traw) type_raw[tc]=type_raw[tc]+1;if(twaw) type_waw[tc]=type_waw[tc]+1;
    if(told) type_old[tc]=type_old[tc]+1;if(tresource) type_resource[tc]=type_resource[tc]+1;
    if(tpred) type_pred[tc]=type_pred[tc]+1;if(talign) type_align[tc]=type_align[tc]+1;
    if(!tplain) type_not_plain[tc]=type_not_plain[tc]+1;
    if(!traw && !twaw && !told && !tresource && !tpred && !CPU.id1_illegal) begin
     type_clean[tc]=type_clean[tc]+1;
     if(tplain && !talign) type_clean_plain[tc]=type_clean_plain[tc]+1;
    end
   end
  end
 end
 always @(negedge clk) if(check_secondary) begin
  for(ti=0;ti<9;ti=ti+1) $display("TYPE_WINDOW category=%0d count=%0d raw=%0d waw=%0d older_dep=%0d resource=%0d prediction=%0d misaligned_branch=%0d nonplain_primary=%0d clean=%0d clean_plain=%0d cross_seen=%0d cross_clean=%0d",ti,type_count[ti],type_raw[ti],type_waw[ti],type_old[ti],type_resource[ti],type_pred[ti],type_align[ti],type_not_plain[ti],type_clean[ti],type_clean_plain[ti],cross_count[ti],cross_clean[ti]);
  $display("FRONT_ORIGIN unexpected=%0d upper_entry=%0d predicted_taken=%0d leftover=%0d other_single=%0d cross_plain_clean=%0d",no_second_reason[0],no_second_reason[1],no_second_reason[2],no_second_reason[3],no_second_reason[4],cross_plain);
 end
'''
 return s.replace('endmodule',block.replace('CPU',cpu)+'\nendmodule')
