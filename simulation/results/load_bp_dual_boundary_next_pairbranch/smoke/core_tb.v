`timescale 1ns/1ps
module core_tb;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[31:0] ticks=0;
 wire iv,ir,iv_rsp,iready,dv,dr,dv_rsp,dready,dwrite;
 wire[63:0] idata;wire[31:0] ia,da,dw,ddata;wire[3:0] mask;
 wire ie,de,tv,tt;wire[31:0] tp,ti,td,tc;wire[4:0] tr;
 reg irq_soft=0,irq_timer=0,irq_ext=0;
 nc_core dut(.clk(clk),.rst_n(rst_n),.irq_soft(irq_soft),.irq_timer(irq_timer),.irq_ext(irq_ext),
  .i_req_valid(iv),.i_req_ready(ir),.i_addr(ia),.i_rsp_valid(iv_rsp),.i_rsp_ready(iready),.i_data(idata),.i_error(ie),
  .d_req_valid(dv),.d_req_ready(dr),.d_addr(da),.d_wdata(dw),.d_mask(mask),.d_write(dwrite),
  .d_rsp_valid(dv_rsp),.d_rsp_ready(dready),.d_rdata(ddata),.d_error(de),
  .trace_valid(tv),.trace_trap(tt),.trace_pc(tp),.trace_insn(ti),.trace_data(td),.trace_cause(tc),.trace_rd(tr));
 reg[31:0] mem[0:24575];
 reg[31:0] lfsr=32'h37a91b21;
 reg ipending=0,dpending=0,irsp=0,drsp=0;
 reg[63:0] iq=0;reg[31:0] dq=0;reg ierr=0,derr=0;
 integer idelay=0,ddelay=0,i,fd,seed=1,limit=2000000,finish_count=0;
 integer retired=0,traps=0,overlap=0;
`ifdef MUL_PIPE_TEST
 integer mul_accepts=0,mul_consumes=0,mul_overlap=0,mul_mem_overlap=0,mul_cancels=0,mul_streak=0,mul_max_streak=0;
 always @(posedge clk) if(rst_n) begin
  if(dut.wb_valid && (!dut.live[dut.w_tag] || dut.w_tag!=dut.head)) $fatal(1,"MUL retirement order/token mismatch");
  if(dut.mul_accept) begin
   mul_accepts=mul_accepts+1;mul_streak=mul_streak+1;
   if(mul_streak>mul_max_streak) mul_max_streak=mul_streak;
   if(dut.multiply.available[dut.ex_tag]) $fatal(1,"MUL token reused before result consumed");
   if(dut.memory.state) mul_mem_overlap=mul_mem_overlap+1;
  end else mul_streak=0;
  if(dut.ex_fire && !dut.ex_multiply && dut.mul_busy) mul_overlap=mul_overlap+1;
  if(dut.mul_consume) begin
   mul_consumes=mul_consumes+1;
   if(!dut.mul_query_ready) $fatal(1,"MUL consumed before result ready");
  end
  if(dut.do_trap && dut.mul_busy) mul_cancels=mul_cancels+1;
  if(dut.m_valid && !dut.live[dut.m_tag]) $fatal(1,"MUL completion for dead token");
 end
`endif
 reg ihold=0,dhold=0;reg[31:0] lastia;reg[68:0] lastd;
 reg[4095:0] image,tracefile;
 function integer index;
 input[31:0] addr;
 begin index=addr<65536 ? addr>>2 : addr>=32'h10000000 && addr<32'h10008000 ? 16384+((addr-32'h10000000)>>2) : -1;end
 endfunction
 assign ir=!ipending && !irsp && lfsr[0];
 assign dr=!dpending && !drsp && lfsr[3];
 assign iv_rsp=irsp;assign dv_rsp=drsp;assign idata=iq;assign ddata=dq;assign ie=ierr;assign de=derr;
 initial begin
  for(i=0;i<24576;i=i+1) mem[i]=0;
  if(!$value$plusargs("image=%s",image)) $fatal(1,"missing image");
  if(!$value$plusargs("trace=%s",tracefile)) tracefile="trace.txt";
  if($value$plusargs("seed=%d",seed)) lfsr=seed;
  if($value$plusargs("limit=%d",limit)) begin end
  $readmemh(image,mem,0,16383);fd=$fopen(tracefile,"w");
  repeat(5) @(negedge clk);rst_n=1;
 end
 always @(posedge clk) if(rst_n) begin
  ticks<=ticks+1;lfsr<={lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};
  if(ticks>limit) $fatal(1,"TIMEOUT pc=%h inflight=%d",tp,dut.inflight);
  if(dut.ex_valid && dut.memory.state!=0) overlap<=overlap+1;
  if(ihold && (!iv || ia!==lastia)) $fatal(1,"IF request changed under backpressure");
  if(dhold && (!dv || {dwrite,mask,dw,da}!==lastd)) $fatal(1,"D request changed under backpressure");
  ihold<=iv && !ir;lastia<=ia;dhold<=dv && !dr;lastd<={dwrite,mask,dw,da};
  if(iv && ir) begin
   ipending<=1;idelay<=1+lfsr[6:4];ierr<=index(ia)<0 || |ia[1:0];
   iq<=index(ia)<0 ? 0 : {mem[index({ia[31:3],3'b100})],mem[index({ia[31:3],3'b000})]};
  end
  if(ipending) begin if(idelay==0) begin ipending<=0;irsp<=1;end else idelay<=idelay-1;end
  if(irsp && iready) irsp<=0;
  if(dv && dr) begin
   dpending<=1;ddelay<=1+lfsr[10:8];dq<=0;derr<=0;
`ifdef MUL_PIPE_TEST
   ddelay<=48+lfsr[10:8];
`endif
   if(index(da)>=0) begin
    dq<=mem[index(da)];
    if(dwrite) for(i=0;i<4;i=i+1) if(mask[i]) mem[index(da)][8*i+:8]<=dw[8*i+:8];
   end else if(da==32'h20003000 && dwrite) begin
    if(dw!=1) $fatal(1,"SOFTWARE_FAIL %h pc=%h",dw,tp);
    finish_count<=20;
`ifdef MUL_PIPE_TEST
    finish_count<=96;
`endif
   end else if(da==32'h20004000 && dwrite) begin
    irq_soft<=dw[0];irq_timer<=dw[1];irq_ext<=dw[2];
   end else derr<=1;
  end
  if(dpending) begin if(ddelay==0) begin dpending<=0;drsp<=1;end else ddelay<=ddelay-1;end
  if(drsp && dready) drsp<=0;
  if(tv) begin
   $fdisplay(fd,"%08x %08x %d %08x %d %08x",tp,ti,tr,td,tt,tc);
   if(tt) traps<=traps+1;else retired<=retired+1;
  end
  if(dut.trace1_valid) begin
   if(!tv || tt) $fatal(1,"Secondary retired without clean primary");
   $fdisplay(fd,"%08x %08x %d %08x 0 00000000",dut.trace1_pc,dut.trace1_insn,dut.trace1_rd,dut.trace1_data);
   retired<=retired+2;
  end
  if(finish_count!=0) begin
   finish_count<=finish_count-1;
   if(finish_count==1) begin
    $display("PASS cycles=%d retired=%d traps=%d overlap=%d",ticks,retired,traps,overlap);
`ifdef MUL_PIPE_TEST
    $display("MUL_CORE accepts=%0d consumes=%0d overlap=%0d mem_overlap=%0d trap_cancels=%0d max_accept_streak=%0d",
     mul_accepts,mul_consumes,mul_overlap,mul_mem_overlap,mul_cancels,mul_max_streak);
`endif
    $fclose(fd);$finish;
   end
  end
 end

 integer pair_issued=0,pair_executed=0,pair_retired=0,pair_squashed_fault=0,dual_streak=0,max_dual_streak=0;
 integer structural=0,dependency_blocked=0,single_issued=0;
 integer win_pairs=0,win_issued=0,win_dep_blocked=0;
 reg check_secondary=0;integer ref_secondary=0;
 always @(posedge clk) if(rst_n) begin
  if(dut.wb_valid && (!dut.live[dut.w_tag] || dut.head!=dut.w_tag)) $fatal(1,"Retirement group out of order");
  if(dut.issue) begin
   if(dut.pair_issue) pair_issued=pair_issued+1;else single_issued=single_issued+1;
   if(dut.id_second) structural=structural+1;
   if(dut.id_second && dut.second_dep) dependency_blocked=dependency_blocked+1;
  end
  if(dut.ex_fire && dut.side_execute) pair_executed=pair_executed+1;
  if(dut.do_trap && dut.w_side[64]) pair_squashed_fault=pair_squashed_fault+1;
  if(dut.commit1) begin
   pair_retired=pair_retired+1;dual_streak=dual_streak+1;
   if(dual_streak>max_dual_streak) max_dual_streak=dual_streak;
   if(!dut.commit || dut.w1_pc!=dut.w_pc+4 || (dut.w_kind==1 && dut.w_next!=dut.w_pc+4) || dut.w_kind==2 || dut.w_kind==3) $fatal(1,"Invalid pair retirement");
   if(dut.w_wr && dut.w_rd!=0 && dut.w_rd==dut.w1_rd) $fatal(1,"RF WAW pair");
  end else dual_streak=0;
  check_secondary=0;
  if(dut.csr.stats.control) begin
   if(dut.csr.stats.control_data[1]) begin ref_secondary=0;win_pairs=0;win_issued=0;win_dep_blocked=0;end
   else if(!dut.csr.stats.control_data[0]) check_secondary=1;
  end else if(dut.csr.stats.enabled) begin
   if(dut.commit1) ref_secondary=ref_secondary+1;
   if(dut.issue) begin
    win_issued=win_issued+1;
    if(dut.pair_issue) win_pairs=win_pairs+1;
    if(dut.id_second && dut.second_dep) win_dep_blocked=win_dep_blocked+1;
   end
  end
 end
 always @(negedge clk) if(check_secondary) begin
  if(dut.csr.stats.counters[10]!=ref_secondary) $fatal(1,"Secondary/reference stats mismatch");
  $display("DUAL_WINDOW secondary_retired=%0d pairs_issued=%0d groups_issued=%0d dependency_blocked=%0d",ref_secondary,win_pairs,win_issued,win_dep_blocked);
 end
 always @(negedge clk) if(finish_count==1) $display("DUAL_STATS issued=%0d executed=%0d retired=%0d fault_cancelled=%0d max_dual_streak=%0d second_visible=%0d dependency_blocked=%0d singles=%0d",pair_issued,pair_executed,pair_retired,pair_squashed_fault,max_dual_streak,structural,dependency_blocked,single_issued);


 always @(posedge clk) if(rst_n) begin
  if(dut.m_valid && dut.m_lane && dut.commit1 && dut.w1_rd!=0 && dut.m_tag==dut.w_tag && dut.m_data!==dut.w1_result) $fatal(1,"MUL/W1 same identity differs");
  if(dut.f1_valid && dut.m_valid && dut.m_lane && dut.f_tag==dut.m_tag && dut.f1_data!==dut.m_data) $fatal(1,"F1/MUL same identity differs");
 end
 

 integer nx_alu=0,nx_load=0,nx_store=0,nx_mul=0,nx_branch=0,nx_other=0,nx_groups=0,nx_kind=0;
 integer nx_pre=0,nx_saved=0,nx_posthold=0,nx_return=0,nx_returnex=0;
 integer nx_last=-1,nx_recovery=0,nx_recovered=0,nx_edge=0;reg[2:0] nx_prevtag;
 reg nx_sidewait;reg nx_exp_m;
 always @(posedge clk) if(rst_n) begin
  nx_edge=nx_edge+1;
  
  if(dut.csr.stats.control && dut.csr.stats.control_data[1]) begin
   nx_alu=0;nx_load=0;nx_store=0;nx_mul=0;nx_branch=0;nx_other=0;nx_groups=0;
   nx_pre=0;nx_saved=0;nx_posthold=0;nx_return=0;nx_returnex=0;
   nx_last=-1;nx_recovery=0;nx_recovered=0;
  end else if(!dut.csr.stats.control && dut.csr.stats.enabled) begin
   nx_sidewait=dut.ex_occupied && !dut.ex_valid && dut.operands.available_a[dut.operands.rd] && dut.operands.available_b[dut.operands.rd];
   if(nx_sidewait) begin
    nx_kind=dut.ex_packet[203:200];
    case(nx_kind) 0:nx_alu=nx_alu+1;4:nx_load=nx_load+1;5:nx_store=nx_store+1;6:nx_mul=nx_mul+1;1,2,3:nx_branch=nx_branch+1;default:nx_other=nx_other+1;endcase
   end
   
   if(dut.branch_event) nx_last=nx_edge;
   if(nx_last>=0 && dut.ex_fire && nx_edge>nx_last && !dut.redirect) begin nx_recovered=nx_recovered+1;nx_recovery=nx_recovery+nx_edge-nx_last;nx_last=-1;end
  end
  
 end
 always @(negedge clk) if(check_secondary) $display("NEXT_WINDOW sidewait_alu=%0d sidewait_load=%0d sidewait_store=%0d sidewait_mul=%0d sidewait_branch=%0d sidewait_other=%0d early_mul=%0d held_response=%0d held_posted=%0d load_return=%0d concurrent_return_ex=%0d recovery_samples=%0d recovery_sum=%0d",nx_alu,nx_load,nx_store,nx_mul,nx_branch,nx_other,nx_pre,nx_saved,nx_posthold,nx_return,nx_returnex,nx_recovered,nx_recovery);


 integer mi_edge=0,mi_st=0,mi_mu=0,mi_ld=0,mi_other=0,mi_headld_st=0,mi_headld_mu=0,mi_headld_ld=0,mi_headld_other=0;
 integer mi_po=0,mi_so=0,mi_both=0,mi_waitld=0,mi_waitmu=0,mi_waitother=0,mi_full=0;
 integer mi_loads=0,mi_directld=0,mi_qloads=0,mi_delay=0,mi_delaymax=0,mi_d0=0,mi_d1=0,mi_d2=0,mi_d3=0,mi_d4=0;
 integer mi_issue_store=0,mi_store_alu=0,mi_store_load=0,mi_store_store=0,mi_store_mul=0;
 integer mi_exload[0:7];reg[1:0] mi_type[0:15];integer mi_i,mi_delta,mi_j;reg mi_p,mi_s,mi_hl,mi_hm,mi_ho;
 reg mi_last_store=0;
 always @(posedge clk) if(rst_n) begin
  mi_edge=mi_edge+1;
  if(dut.issue) begin
   mi_type[{dut.tail,1'b0}]=dut.id_kind==4 ? 1 : dut.id_kind==6 ? 2 : 0;
   mi_type[{dut.tail,1'b1}]=dut.id_side_kind==6 ? 2 : 0;
  end
  if(dut.ex_fire && dut.ex_packet[203:200]==4) mi_exload[dut.ex_tag]=mi_edge;
  if(dut.csr.stats.control && dut.csr.stats.control_data[1]) begin
   mi_st=0;mi_mu=0;mi_ld=0;mi_other=0;mi_headld_st=0;mi_headld_mu=0;mi_headld_ld=0;mi_headld_other=0;
   mi_po=0;mi_so=0;mi_both=0;mi_waitld=0;mi_waitmu=0;mi_waitother=0;mi_full=0;
   mi_loads=0;mi_directld=0;mi_qloads=0;mi_delay=0;mi_delaymax=0;mi_d0=0;mi_d1=0;mi_d2=0;mi_d3=0;mi_d4=0;
   mi_last_store=0;mi_issue_store=0;mi_store_alu=0;mi_store_load=0;mi_store_store=0;mi_store_mul=0;
  end else if(!dut.csr.stats.control && dut.csr.stats.enabled) begin
   if(!dut.memory_ready && !dut.do_trap) begin
    if(dut.memory.memory_access && dut.memory.kind==5) mi_st=mi_st+1;
    else if(dut.memory.multiply_access && !dut.mul_query_ready) mi_mu=mi_mu+1;
    else if(dut.memory.memory_access && dut.memory.kind==4) mi_ld=mi_ld+1;
    else mi_other=mi_other+1;
    if(dut.queued_valid && dut.queued_packet[7:4]==4) begin
     if(dut.memory.memory_access && dut.memory.kind==5) mi_headld_st=mi_headld_st+1;
     else if(dut.memory.multiply_access && !dut.mul_query_ready) mi_headld_mu=mi_headld_mu+1;
     else if(dut.memory.memory_access && dut.memory.kind==4) mi_headld_ld=mi_headld_ld+1;
     else mi_headld_other=mi_headld_other+1;
    end
   end
   if(dut.execute_valid && !dut.mem_credit) mi_full=mi_full+1;
   if(dut.ex_occupied && !dut.ex_valid) begin
    mi_p=!dut.operands.available_a[dut.operands.rd] || !dut.operands.available_b[dut.operands.rd];
    mi_s=!dut.operands.available_c[dut.operands.rd] || !dut.operands.available_d[dut.operands.rd];
    if(mi_p && mi_s) mi_both=mi_both+1;else if(mi_p) mi_po=mi_po+1;else if(mi_s) mi_so=mi_so+1;
    mi_hl=0;mi_hm=0;mi_ho=0;
    for(mi_i=0;mi_i<4;mi_i=mi_i+1) begin
     case(mi_i)
      0:begin mi_j=dut.operands.dep_a[dut.operands.rd];mi_hl=mi_hl || (!dut.operands.available_a[dut.operands.rd] && mi_type[mi_j]==1);mi_hm=mi_hm || (!dut.operands.available_a[dut.operands.rd] && mi_type[mi_j]==2);end
      1:begin mi_j=dut.operands.dep_b[dut.operands.rd];mi_hl=mi_hl || (!dut.operands.available_b[dut.operands.rd] && mi_type[mi_j]==1);mi_hm=mi_hm || (!dut.operands.available_b[dut.operands.rd] && mi_type[mi_j]==2);end
      2:begin mi_j=dut.operands.dep_c[dut.operands.rd];mi_hl=mi_hl || (!dut.operands.available_c[dut.operands.rd] && mi_type[mi_j]==1);mi_hm=mi_hm || (!dut.operands.available_c[dut.operands.rd] && mi_type[mi_j]==2);end
      3:begin mi_j=dut.operands.dep_d[dut.operands.rd];mi_hl=mi_hl || (!dut.operands.available_d[dut.operands.rd] && mi_type[mi_j]==1);mi_hm=mi_hm || (!dut.operands.available_d[dut.operands.rd] && mi_type[mi_j]==2);end
     endcase
    end
    if(mi_hl) mi_waitld=mi_waitld+1;if(mi_hm) mi_waitmu=mi_waitmu+1;if(!mi_hl && !mi_hm) mi_waitother=mi_waitother+1;
   end
   if(dut.memory.start) begin
    if(mi_last_store) begin
     case(dut.mem_packet[7:4]) 4:mi_store_load=mi_store_load+1;5:mi_store_store=mi_store_store+1;6:mi_store_mul=mi_store_mul+1;default:mi_store_alu=mi_store_alu+1;endcase
    end
    mi_last_store=dut.mem_packet[7:4]==5;
    if(mi_last_store) mi_issue_store=mi_issue_store+1;
    if(dut.mem_packet[7:4]==4) begin
     mi_loads=mi_loads+1;if(dut.direct_take) mi_directld=mi_directld+1;else mi_qloads=mi_qloads+1;
     mi_delta=mi_edge-mi_exload[dut.mem_packet[279:277]];mi_delay=mi_delay+mi_delta;if(mi_delta>mi_delaymax) mi_delaymax=mi_delta;
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


 integer br_mem=0,br_early=0,br_direct=0,br_spill=0,br_stall=0;
 always @(posedge clk) if(rst_n) begin
  if(dut.csr.stats.control && dut.csr.stats.control_data[1]) begin br_mem=0;br_early=0;br_direct=0;br_spill=0;br_stall=0;end
  else if(!dut.csr.stats.control && dut.csr.stats.enabled) begin
   if(dut.memory.start && dut.memory.input_memory) br_mem=br_mem+1;
   if(dut.memory.early_request && dut.d_req_ready) br_early=br_early+1;
   if(dut.direct_take) br_direct=br_direct+1;
   if(dut.execute_valid && dut.mem_credit && !dut.direct_take) br_spill=br_spill+1;
   if(dut.memory.slot_valid && !dut.memory.complete) br_stall=br_stall+1;
  end
  if(dut.direct_take && !dut.ex_fire) $fatal(1,"Direct MEM ownership without EX transfer");
  if(dut.memory.early_request && (!dut.memory.start || dut.memory.old_request || dut.memory.exception && dut.memory.slot_valid)) $fatal(1,"Invalid early ownership");
 end
 always @(negedge clk) if(check_secondary) $display("BOUNDARY_WINDOW memory_groups=%0d early_accept=%0d direct=%0d spilled=%0d slot_stall=%0d",br_mem,br_early,br_direct,br_spill,br_stall);


 integer j_cross=0,j_pop2=0,j_primary_branch=0,j_branch=0,j_mul=0,j_alu=0,j_wait_pair=0;
 integer j_dep=0,j_nosecond=0,j_class=0,j_misses=0,j_probes=0;
 reg[3:0] j_t;reg j_has;integer jn;reg j_found;
 always @(posedge clk) if(rst_n) begin
  if(dut.ex_valid && dut.ex_side[223] && (dut.operands.wc[dut.operands.rd] || dut.operands.wd[dut.operands.rd])) begin
   if(!dut.operands.available_c[dut.operands.rd] || !dut.operands.available_d[dut.operands.rd]) $fatal(1,"Execute with unavailable secondary source");
  end
  if(dut.pair_issue && dut.fetch.head_1[106:75]!=dut.id_pc+4) $fatal(1,"Cross-group adjacency");
  if(dut.pair_issue && dut.id_kind==1 && dut.id_side_kind==1) $fatal(1,"Two branches admitted to one group");
  // Scoreboard youngest-producer check uses instruction order, not the DUT's
  // wrapped priority encoder. Lane1 follows lane0 within each live group.
  if(dut.issue && dut.pair_candidate) begin
   for(jn=0;jn<2;jn=jn+1) begin
    j_t=0;j_has=0;
    begin:check_age
     integer age,idx;reg[4:0] rs;
     rs=jn==0 ? dut.rs1_1 : dut.rs2_1;
     if((jn==0 ? dut.id_pair_flags[5] : dut.id_pair_flags[6]) && rs!=0) begin
      for(age=0;age<8;age=age+1) begin
       idx=(dut.tail+age)&7;
       if(dut.live[idx]) begin
        if(dut.destination[idx]==rs) begin j_t={idx[2:0],1'b0};j_has=1;end
        if(dut.destination1[idx]==rs) begin j_t={idx[2:0],1'b1};j_has=1;end
       end
      end
     end
    end
    if((jn==0 ? dut.dep_c : dut.dep_d)!==j_has || (j_has && (jn==0 ? dut.tag_c : dut.tag_d)!==j_t)) $fatal(1,"Secondary youngest producer mismatch");
   end
  end
  if(dut.csr.stats.control && dut.csr.stats.control_data[1]) begin
   j_cross=0;j_pop2=0;j_primary_branch=0;j_branch=0;j_mul=0;j_alu=0;j_wait_pair=0;
   j_dep=0;j_nosecond=0;j_class=0;j_misses=0;j_probes=0;
  end else if(!dut.csr.stats.control && dut.csr.stats.enabled) begin
   if(dut.issue) begin
    if(!dut.id_second) j_nosecond=j_nosecond+1;
    else if(dut.second_dep) j_dep=j_dep+1;
    if(dut.pair_issue) begin
     if(dut.fetch.rd[0]) j_cross=j_cross+1;
     if(dut.dep_c || dut.dep_d) j_wait_pair=j_wait_pair+1;
    end
   end
   if((dut.fetch.consume && dut.fetch.pop_two)) j_pop2=j_pop2+1;
   if(dut.commit1) begin
    if(dut.w_kind==1) j_primary_branch=j_primary_branch+1;
    if(dut.w1_branch) j_branch=j_branch+1;
    else if(dut.w1_insn[6:0]==7'h33 && dut.w1_insn[31:25]==1) j_mul=j_mul+1;
    else j_alu=j_alu+1;
   end
  end
 end
 always @(negedge clk) if(check_secondary) begin
  if(j_branch+j_mul+j_alu!=ref_secondary) $fatal(1,"Slot census mismatch");
  $display("JOINT_WINDOW cross=%0d pop2=%0d primary_branch=%0d branch=%0d mul=%0d alu=%0d dependent_pairs=%0d dependency_split=%0d no_second=%0d",j_cross,j_pop2,j_primary_branch,j_branch,j_mul,j_alu,j_wait_pair,j_dep,j_nosecond);
 end

endmodule
