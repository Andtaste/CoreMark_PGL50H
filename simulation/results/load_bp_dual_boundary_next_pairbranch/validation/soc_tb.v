`timescale 1ns/1ps
module soc_tb;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;
 wire tx;wire[1:0] gpio;wire[31:0] tohost;
 nc_soc dut(.clk(clk),.rst_n(rst_n),.irq_soft(1'b0),.irq_ext(1'b0),.uart_tx(tx),.gpio_out(gpio),.tohost(tohost));
`ifdef COREMARK_SIM
 // Reporting is outside the measured window; speed UART only, never CPU/RAM.

 localparam UART_DIV=8;
 integer ref_cycles=0,ref_retired=0,ref_loads=0,ref_stores=0,ref_bjp=0;
 reg check_stats=0;
 integer bp_resolved=0,bp_hits=0,bp_taken=0,bp_direction_wrong=0,bp_target_wrong=0,bp_wrong=0,bp_nonbranch_wrong=0;
 integer bp_recovery_empty=0;reg bp_recovering=0;
 integer mul_accepted=0,mul_completed=0,mul_head_wait=0,mul_overlapped=0,mul_memory_overlap=0;
 integer mul_accept_streak=0,mul_max_streak=0;
 // Independent opcode classification and direct window accumulation.
 // Compare after stop's clock edge has drained the hardware sample register.
 always @(posedge clk) if(rst_n) begin
  check_stats=0;
  if(dut.cpu.csr.stats.control) begin
   if(dut.cpu.csr.stats.control_data[1]) begin
    ref_cycles=0;ref_retired=0;ref_loads=0;ref_stores=0;ref_bjp=0;
    bp_resolved=0;bp_hits=0;bp_taken=0;bp_direction_wrong=0;bp_target_wrong=0;
    bp_wrong=0;bp_nonbranch_wrong=0;bp_recovery_empty=0;bp_recovering=0;
    mul_accepted=0;mul_completed=0;mul_head_wait=0;mul_overlapped=0;mul_memory_overlap=0;
    mul_accept_streak=0;mul_max_streak=0;
   end else if(!dut.cpu.csr.stats.control_data[0]) check_stats=1;
  end else if(dut.cpu.csr.stats.enabled) begin
   ref_cycles=ref_cycles+1;
   if(dut.cpu.mul_accept) begin
    mul_accepted=mul_accepted+1;mul_accept_streak=mul_accept_streak+1;
    if(mul_accept_streak>mul_max_streak) mul_max_streak=mul_accept_streak;
   end else mul_accept_streak=0;
   if(dut.cpu.m_valid) mul_completed=mul_completed+1;
   if(dut.cpu.memory.slot_valid && dut.cpu.memory.multiply_access &&
      !dut.cpu.mul_query_ready) mul_head_wait=mul_head_wait+1;
   if(dut.cpu.ex_fire && !dut.cpu.ex_multiply && dut.cpu.mul_busy) mul_overlapped=mul_overlapped+1;
   if(dut.cpu.mul_accept && dut.cpu.memory.state) mul_memory_overlap=mul_memory_overlap+1;
   if(bp_recovering && !dut.cpu.id_valid) bp_recovery_empty=bp_recovery_empty+1;
   if(dut.cpu.branch_event) bp_recovering=1;
   else if(dut.cpu.id_valid && !dut.cpu.redirect) bp_recovering=0;
   if(dut.cpu.ex_fire && !dut.cpu.execute_packet[2]) begin
    if(dut.cpu.resolved_branch) begin
     bp_resolved=bp_resolved+1;
     if(dut.cpu.resolved_prediction[31]) bp_hits=bp_hits+1;
     if(dut.cpu.resolved_prediction[30]) bp_taken=bp_taken+1;
     if(dut.cpu.resolved_prediction[30]!=dut.cpu.resolved_taken) bp_direction_wrong=bp_direction_wrong+1;
     if(dut.cpu.resolved_prediction[30] && dut.cpu.resolved_taken &&
        {dut.cpu.resolved_prediction[29:0],2'b0}!=dut.cpu.resolved_target) bp_target_wrong=bp_target_wrong+1;
     if(dut.cpu.branch_event) bp_wrong=bp_wrong+1;
    end else if(dut.cpu.branch_event) bp_nonbranch_wrong=bp_nonbranch_wrong+1;
   end
   if(dut.cpu.commit) begin
    ref_retired=ref_retired+(dut.cpu.commit1 ? 2 : 1);
    if(dut.cpu.commit1 && dut.cpu.w1_branch) ref_bjp=ref_bjp+1;
    case(dut.cpu.w_insn[6:0])
     7'h03:ref_loads=ref_loads+1;
     7'h23:ref_stores=ref_stores+1;
     7'h63,7'h6f,7'h67:ref_bjp=ref_bjp+1;
    endcase
   end
  end
 end
 always @(negedge clk) if(check_stats) begin
  if(dut.cpu.csr.stats.counters[1]!=ref_cycles ||
     dut.cpu.csr.stats.counters[9]!=ref_retired ||
     dut.cpu.csr.stats.counters[11]!=ref_loads ||
     dut.cpu.csr.stats.counters[12]!=ref_stores ||
     dut.cpu.csr.stats.counters[7]!=ref_bjp)
   $fatal(1,"Stats/reference window or opcode counts differ");
  $display("COUNTER_CHECK_PASS cycles=%0d retired=%0d loads=%0d stores=%0d bjp=%0d",
   ref_cycles,ref_retired,ref_loads,ref_stores,ref_bjp);
  $display("PREDICTOR_STATS enabled=%0d resolved=%0d hits=%0d predicted_taken=%0d direction_wrong=%0d target_wrong=%0d next_pc_wrong=%0d nonbranch_wrong=%0d recovery_if_empty=%0d",
   dut.cpu.ENABLE_BP,bp_resolved,bp_hits,bp_taken,bp_direction_wrong,bp_target_wrong,bp_wrong,bp_nonbranch_wrong,bp_recovery_empty);
  $display("MULTIPLY_STATS accepted=%0d completed=%0d head_wait=%0d overlapped=%0d memory_overlap=%0d max_accept_streak=%0d",
   mul_accepted,mul_completed,mul_head_wait,mul_overlapped,mul_memory_overlap,mul_max_streak);
 end
`else
 localparam UART_DIV=651;
`endif
 integer ticks=0,finish_count=0,fd,retired=0,streak=0,max_streak=0,limit=10000000,legacy=0;
 reg[4095:0] tracefile,uartfile;
 integer uart_fd,bit_index,notrace=0;reg[7:0] uart_byte;
 initial begin
  if(!$value$plusargs("trace=%s",tracefile)) tracefile="soc.trace";
  if($value$plusargs("limit=%d",limit)) begin end
  if($value$plusargs("legacy=%d",legacy)) begin end
  if($value$plusargs("notrace=%d",notrace)) begin end
  if(!$value$plusargs("uart=%s",uartfile)) uartfile="simulation/results/uart.out";
  fd=$fopen(tracefile,"w");uart_fd=$fopen(uartfile,"wb");
  repeat(5) @(negedge clk);rst_n=1;
 end
 // Independently decode the actual UART wire, not the MMIO write data.
 initial forever begin
  @(negedge tx);
  if(rst_n) begin
   repeat(UART_DIV/2) @(posedge clk);
   if(tx!==0) $fatal(1,"UART invalid start");
   for(bit_index=0;bit_index<8;bit_index=bit_index+1) begin
    repeat(UART_DIV) @(posedge clk);uart_byte[bit_index]=tx;
   end
   repeat(UART_DIV) @(posedge clk);
   if(tx!==1) $fatal(1,"UART invalid stop");
   $fwrite(uart_fd,"%c",uart_byte);$fflush(uart_fd);
  end
 end
 always @(posedge clk) if(rst_n) begin
  if(dut.cpu.m_valid && !dut.cpu.m_lane && dut.cpu.commit && dut.cpu.w_wr && dut.cpu.w_rd!=0 &&
     dut.cpu.m_tag==dut.cpu.w_tag && dut.cpu.m_data!==dut.cpu.w_result)
   $fatal(1,"MUL/WB duplicate tag has different values");
  if(dut.cpu.f_valid && dut.cpu.commit && dut.cpu.w_wr && dut.cpu.w_rd!=0 &&
     dut.cpu.f_tag==dut.cpu.w_tag && dut.cpu.f_data!==dut.cpu.w_result)
   $fatal(1,"EX/WB duplicate tag has different values");
  if(dut.cpu.f_valid && dut.cpu.m_valid && !dut.cpu.m_lane && dut.cpu.f_tag==dut.cpu.m_tag &&
     dut.cpu.f_data!==dut.cpu.m_data) $fatal(1,"EX/MUL duplicate tag has different values");
  ticks<=ticks+1;
  if(ticks>limit) $fatal(1,"SOC TIMEOUT pc=%h",dut.cpu.trace_pc);
  if(dut.cpu.wb_valid && (!dut.cpu.live[dut.cpu.w_tag] || dut.cpu.w_tag!=dut.cpu.head))
   $fatal(1,"Retirement order/token mismatch");
  if(dut.cpu.trace_valid) begin
   retired<=retired+1;streak<=streak+1;if(streak+1>max_streak) max_streak<=streak+1;
   if(!notrace) $fdisplay(fd,"%08x %08x %d %08x %d %08x",dut.cpu.trace_pc,dut.cpu.trace_insn,
    dut.cpu.trace_rd,dut.cpu.trace_data,dut.cpu.trace_trap,dut.cpu.trace_cause);
  end else streak<=0;
  if(dut.cpu.trace1_valid) begin
   if(!dut.cpu.trace_valid || dut.cpu.trace_trap) $fatal(1,"Secondary retired without clean primary");
   retired<=retired+2;
   if(!notrace) $fdisplay(fd,"%08x %08x %d %08x 0 00000000",dut.cpu.trace1_pc,dut.cpu.trace1_insn,dut.cpu.trace1_rd,dut.cpu.trace1_data);
  end
  if(tohost!=0 && finish_count==0) begin
   if(tohost!=1) $fatal(1,"SOC software failure %h",tohost);
   finish_count<=20;
  end
  if(legacy!=0 && dut.cpu.rf.regs[26]===32'd1 && finish_count==0) finish_count<=20;
  if(finish_count!=0) begin
   finish_count<=finish_count-1;
   if(finish_count==1) begin
    if(legacy!=0 && dut.cpu.rf.regs[27]!==32'd1) $fatal(1,"ISA software failure gp=%h",dut.cpu.rf.regs[3]);
    $display("PASS cycles=%d retired=%d max_retire_streak=%d",ticks,retired,max_streak);
    $fclose(fd);$fclose(uart_fd);$finish;
   end
  end
 end

 integer pair_issued=0,pair_executed=0,pair_retired=0,pair_squashed_fault=0,dual_streak=0,max_dual_streak=0;
 integer structural=0,dependency_blocked=0,single_issued=0;
 integer win_pairs=0,win_issued=0,win_dep_blocked=0;
 reg check_secondary=0;integer ref_secondary=0;
 always @(posedge clk) if(rst_n) begin
  if(dut.cpu.wb_valid && (!dut.cpu.live[dut.cpu.w_tag] || dut.cpu.head!=dut.cpu.w_tag)) $fatal(1,"Retirement group out of order");
  if(dut.cpu.issue) begin
   if(dut.cpu.pair_issue) pair_issued=pair_issued+1;else single_issued=single_issued+1;
   if(dut.cpu.id_second) structural=structural+1;
   if(dut.cpu.id_second && dut.cpu.second_dep) dependency_blocked=dependency_blocked+1;
  end
  if(dut.cpu.ex_fire && dut.cpu.side_execute) pair_executed=pair_executed+1;
  if(dut.cpu.do_trap && dut.cpu.w_side[64]) pair_squashed_fault=pair_squashed_fault+1;
  if(dut.cpu.commit1) begin
   pair_retired=pair_retired+1;dual_streak=dual_streak+1;
   if(dual_streak>max_dual_streak) max_dual_streak=dual_streak;
   if(!dut.cpu.commit || dut.cpu.w1_pc!=dut.cpu.w_pc+4 || (dut.cpu.w_kind==1 && dut.cpu.w_next!=dut.cpu.w_pc+4) || dut.cpu.w_kind==2 || dut.cpu.w_kind==3) $fatal(1,"Invalid pair retirement");
   if(dut.cpu.w_wr && dut.cpu.w_rd!=0 && dut.cpu.w_rd==dut.cpu.w1_rd) $fatal(1,"RF WAW pair");
  end else dual_streak=0;
  check_secondary=0;
  if(dut.cpu.csr.stats.control) begin
   if(dut.cpu.csr.stats.control_data[1]) begin ref_secondary=0;win_pairs=0;win_issued=0;win_dep_blocked=0;end
   else if(!dut.cpu.csr.stats.control_data[0]) check_secondary=1;
  end else if(dut.cpu.csr.stats.enabled) begin
   if(dut.cpu.commit1) ref_secondary=ref_secondary+1;
   if(dut.cpu.issue) begin
    win_issued=win_issued+1;
    if(dut.cpu.pair_issue) win_pairs=win_pairs+1;
    if(dut.cpu.id_second && dut.cpu.second_dep) win_dep_blocked=win_dep_blocked+1;
   end
  end
 end
 always @(negedge clk) if(check_secondary) begin
  if(dut.cpu.csr.stats.counters[10]!=ref_secondary) $fatal(1,"Secondary/reference stats mismatch");
  $display("DUAL_WINDOW secondary_retired=%0d pairs_issued=%0d groups_issued=%0d dependency_blocked=%0d",ref_secondary,win_pairs,win_issued,win_dep_blocked);
 end
 always @(negedge clk) if(finish_count==1) $display("DUAL_STATS issued=%0d executed=%0d retired=%0d fault_cancelled=%0d max_dual_streak=%0d second_visible=%0d dependency_blocked=%0d singles=%0d",pair_issued,pair_executed,pair_retired,pair_squashed_fault,max_dual_streak,structural,dependency_blocked,single_issued);


 always @(posedge clk) if(rst_n) begin
  if(dut.cpu.m_valid && dut.cpu.m_lane && dut.cpu.commit1 && dut.cpu.w1_rd!=0 && dut.cpu.m_tag==dut.cpu.w_tag && dut.cpu.m_data!==dut.cpu.w1_result) $fatal(1,"MUL/W1 same identity differs");
  if(dut.cpu.f1_valid && dut.cpu.m_valid && dut.cpu.m_lane && dut.cpu.f_tag==dut.cpu.m_tag && dut.cpu.f1_data!==dut.cpu.m_data) $fatal(1,"F1/MUL same identity differs");
 end
 

 integer nx_alu=0,nx_load=0,nx_store=0,nx_mul=0,nx_branch=0,nx_other=0,nx_groups=0,nx_kind=0;
 integer nx_pre=0,nx_saved=0,nx_posthold=0,nx_return=0,nx_returnex=0;
 integer nx_last=-1,nx_recovery=0,nx_recovered=0,nx_edge=0;reg[2:0] nx_prevtag;
 reg nx_sidewait;reg nx_exp_m;
 always @(posedge clk) if(rst_n) begin
  nx_edge=nx_edge+1;
  
  if(dut.cpu.csr.stats.control && dut.cpu.csr.stats.control_data[1]) begin
   nx_alu=0;nx_load=0;nx_store=0;nx_mul=0;nx_branch=0;nx_other=0;nx_groups=0;
   nx_pre=0;nx_saved=0;nx_posthold=0;nx_return=0;nx_returnex=0;
   nx_last=-1;nx_recovery=0;nx_recovered=0;
  end else if(!dut.cpu.csr.stats.control && dut.cpu.csr.stats.enabled) begin
   nx_sidewait=dut.cpu.ex_occupied && !dut.cpu.ex_valid && dut.cpu.operands.available_a[dut.cpu.operands.rd] && dut.cpu.operands.available_b[dut.cpu.operands.rd];
   if(nx_sidewait) begin
    nx_kind=dut.cpu.ex_packet[203:200];
    case(nx_kind) 0:nx_alu=nx_alu+1;4:nx_load=nx_load+1;5:nx_store=nx_store+1;6:nx_mul=nx_mul+1;1,2,3:nx_branch=nx_branch+1;default:nx_other=nx_other+1;endcase
   end
   
   if(dut.cpu.branch_event) nx_last=nx_edge;
   if(nx_last>=0 && dut.cpu.ex_fire && nx_edge>nx_last && !dut.cpu.redirect) begin nx_recovered=nx_recovered+1;nx_recovery=nx_recovery+nx_edge-nx_last;nx_last=-1;end
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
  if(dut.cpu.issue) begin
   mi_type[{dut.cpu.tail,1'b0}]=dut.cpu.id_kind==4 ? 1 : dut.cpu.id_kind==6 ? 2 : 0;
   mi_type[{dut.cpu.tail,1'b1}]=dut.cpu.id_side_kind==6 ? 2 : 0;
  end
  if(dut.cpu.ex_fire && dut.cpu.ex_packet[203:200]==4) mi_exload[dut.cpu.ex_tag]=mi_edge;
  if(dut.cpu.csr.stats.control && dut.cpu.csr.stats.control_data[1]) begin
   mi_st=0;mi_mu=0;mi_ld=0;mi_other=0;mi_headld_st=0;mi_headld_mu=0;mi_headld_ld=0;mi_headld_other=0;
   mi_po=0;mi_so=0;mi_both=0;mi_waitld=0;mi_waitmu=0;mi_waitother=0;mi_full=0;
   mi_loads=0;mi_directld=0;mi_qloads=0;mi_delay=0;mi_delaymax=0;mi_d0=0;mi_d1=0;mi_d2=0;mi_d3=0;mi_d4=0;
   mi_last_store=0;mi_issue_store=0;mi_store_alu=0;mi_store_load=0;mi_store_store=0;mi_store_mul=0;
  end else if(!dut.cpu.csr.stats.control && dut.cpu.csr.stats.enabled) begin
   if(!dut.cpu.memory_ready && !dut.cpu.do_trap) begin
    if(dut.cpu.memory.memory_access && dut.cpu.memory.kind==5) mi_st=mi_st+1;
    else if(dut.cpu.memory.multiply_access && !dut.cpu.mul_query_ready) mi_mu=mi_mu+1;
    else if(dut.cpu.memory.memory_access && dut.cpu.memory.kind==4) mi_ld=mi_ld+1;
    else mi_other=mi_other+1;
    if(dut.cpu.queued_valid && dut.cpu.queued_packet[7:4]==4) begin
     if(dut.cpu.memory.memory_access && dut.cpu.memory.kind==5) mi_headld_st=mi_headld_st+1;
     else if(dut.cpu.memory.multiply_access && !dut.cpu.mul_query_ready) mi_headld_mu=mi_headld_mu+1;
     else if(dut.cpu.memory.memory_access && dut.cpu.memory.kind==4) mi_headld_ld=mi_headld_ld+1;
     else mi_headld_other=mi_headld_other+1;
    end
   end
   if(dut.cpu.execute_valid && !dut.cpu.mem_credit) mi_full=mi_full+1;
   if(dut.cpu.ex_occupied && !dut.cpu.ex_valid) begin
    mi_p=!dut.cpu.operands.available_a[dut.cpu.operands.rd] || !dut.cpu.operands.available_b[dut.cpu.operands.rd];
    mi_s=!dut.cpu.operands.available_c[dut.cpu.operands.rd] || !dut.cpu.operands.available_d[dut.cpu.operands.rd];
    if(mi_p && mi_s) mi_both=mi_both+1;else if(mi_p) mi_po=mi_po+1;else if(mi_s) mi_so=mi_so+1;
    mi_hl=0;mi_hm=0;mi_ho=0;
    for(mi_i=0;mi_i<4;mi_i=mi_i+1) begin
     case(mi_i)
      0:begin mi_j=dut.cpu.operands.dep_a[dut.cpu.operands.rd];mi_hl=mi_hl || (!dut.cpu.operands.available_a[dut.cpu.operands.rd] && mi_type[mi_j]==1);mi_hm=mi_hm || (!dut.cpu.operands.available_a[dut.cpu.operands.rd] && mi_type[mi_j]==2);end
      1:begin mi_j=dut.cpu.operands.dep_b[dut.cpu.operands.rd];mi_hl=mi_hl || (!dut.cpu.operands.available_b[dut.cpu.operands.rd] && mi_type[mi_j]==1);mi_hm=mi_hm || (!dut.cpu.operands.available_b[dut.cpu.operands.rd] && mi_type[mi_j]==2);end
      2:begin mi_j=dut.cpu.operands.dep_c[dut.cpu.operands.rd];mi_hl=mi_hl || (!dut.cpu.operands.available_c[dut.cpu.operands.rd] && mi_type[mi_j]==1);mi_hm=mi_hm || (!dut.cpu.operands.available_c[dut.cpu.operands.rd] && mi_type[mi_j]==2);end
      3:begin mi_j=dut.cpu.operands.dep_d[dut.cpu.operands.rd];mi_hl=mi_hl || (!dut.cpu.operands.available_d[dut.cpu.operands.rd] && mi_type[mi_j]==1);mi_hm=mi_hm || (!dut.cpu.operands.available_d[dut.cpu.operands.rd] && mi_type[mi_j]==2);end
     endcase
    end
    if(mi_hl) mi_waitld=mi_waitld+1;if(mi_hm) mi_waitmu=mi_waitmu+1;if(!mi_hl && !mi_hm) mi_waitother=mi_waitother+1;
   end
   if(dut.cpu.memory.start) begin
    if(mi_last_store) begin
     case(dut.cpu.mem_packet[7:4]) 4:mi_store_load=mi_store_load+1;5:mi_store_store=mi_store_store+1;6:mi_store_mul=mi_store_mul+1;default:mi_store_alu=mi_store_alu+1;endcase
    end
    mi_last_store=dut.cpu.mem_packet[7:4]==5;
    if(mi_last_store) mi_issue_store=mi_issue_store+1;
    if(dut.cpu.mem_packet[7:4]==4) begin
     mi_loads=mi_loads+1;if(dut.cpu.direct_take) mi_directld=mi_directld+1;else mi_qloads=mi_qloads+1;
     mi_delta=mi_edge-mi_exload[dut.cpu.mem_packet[279:277]];mi_delay=mi_delay+mi_delta;if(mi_delta>mi_delaymax) mi_delaymax=mi_delta;
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
  if(dut.cpu.csr.stats.control && dut.cpu.csr.stats.control_data[1]) begin br_mem=0;br_early=0;br_direct=0;br_spill=0;br_stall=0;end
  else if(!dut.cpu.csr.stats.control && dut.cpu.csr.stats.enabled) begin
   if(dut.cpu.memory.start && dut.cpu.memory.input_memory) br_mem=br_mem+1;
   if(dut.cpu.memory.early_request && dut.cpu.d_req_ready) br_early=br_early+1;
   if(dut.cpu.direct_take) br_direct=br_direct+1;
   if(dut.cpu.execute_valid && dut.cpu.mem_credit && !dut.cpu.direct_take) br_spill=br_spill+1;
   if(dut.cpu.memory.slot_valid && !dut.cpu.memory.complete) br_stall=br_stall+1;
  end
  if(dut.cpu.direct_take && !dut.cpu.ex_fire) $fatal(1,"Direct MEM ownership without EX transfer");
  if(dut.cpu.memory.early_request && (!dut.cpu.memory.start || dut.cpu.memory.old_request || dut.cpu.memory.exception && dut.cpu.memory.slot_valid)) $fatal(1,"Invalid early ownership");
 end
 always @(negedge clk) if(check_secondary) $display("BOUNDARY_WINDOW memory_groups=%0d early_accept=%0d direct=%0d spilled=%0d slot_stall=%0d",br_mem,br_early,br_direct,br_spill,br_stall);


 integer j_cross=0,j_pop2=0,j_primary_branch=0,j_branch=0,j_mul=0,j_alu=0,j_wait_pair=0;
 integer j_dep=0,j_nosecond=0,j_class=0,j_misses=0,j_probes=0;
 reg[3:0] j_t;reg j_has;integer jn;reg j_found;
 always @(posedge clk) if(rst_n) begin
  if(dut.cpu.ex_valid && dut.cpu.ex_side[223] && (dut.cpu.operands.wc[dut.cpu.operands.rd] || dut.cpu.operands.wd[dut.cpu.operands.rd])) begin
   if(!dut.cpu.operands.available_c[dut.cpu.operands.rd] || !dut.cpu.operands.available_d[dut.cpu.operands.rd]) $fatal(1,"Execute with unavailable secondary source");
  end
  if(dut.cpu.pair_issue && dut.cpu.fetch.head_1[106:75]!=dut.cpu.id_pc+4) $fatal(1,"Cross-group adjacency");
  if(dut.cpu.pair_issue && dut.cpu.id_kind==1 && dut.cpu.id_side_kind==1) $fatal(1,"Two branches admitted to one group");
  // Scoreboard youngest-producer check uses instruction order, not the DUT's
  // wrapped priority encoder. Lane1 follows lane0 within each live group.
  if(dut.cpu.issue && dut.cpu.pair_candidate) begin
   for(jn=0;jn<2;jn=jn+1) begin
    j_t=0;j_has=0;
    begin:check_age
     integer age,idx;reg[4:0] rs;
     rs=jn==0 ? dut.cpu.rs1_1 : dut.cpu.rs2_1;
     if((jn==0 ? dut.cpu.id_pair_flags[5] : dut.cpu.id_pair_flags[6]) && rs!=0) begin
      for(age=0;age<8;age=age+1) begin
       idx=(dut.cpu.tail+age)&7;
       if(dut.cpu.live[idx]) begin
        if(dut.cpu.destination[idx]==rs) begin j_t={idx[2:0],1'b0};j_has=1;end
        if(dut.cpu.destination1[idx]==rs) begin j_t={idx[2:0],1'b1};j_has=1;end
       end
      end
     end
    end
    if((jn==0 ? dut.cpu.dep_c : dut.cpu.dep_d)!==j_has || (j_has && (jn==0 ? dut.cpu.tag_c : dut.cpu.tag_d)!==j_t)) $fatal(1,"Secondary youngest producer mismatch");
   end
  end
  if(dut.cpu.csr.stats.control && dut.cpu.csr.stats.control_data[1]) begin
   j_cross=0;j_pop2=0;j_primary_branch=0;j_branch=0;j_mul=0;j_alu=0;j_wait_pair=0;
   j_dep=0;j_nosecond=0;j_class=0;j_misses=0;j_probes=0;
  end else if(!dut.cpu.csr.stats.control && dut.cpu.csr.stats.enabled) begin
   if(dut.cpu.issue) begin
    if(!dut.cpu.id_second) j_nosecond=j_nosecond+1;
    else if(dut.cpu.second_dep) j_dep=j_dep+1;
    if(dut.cpu.pair_issue) begin
     if(dut.cpu.fetch.rd[0]) j_cross=j_cross+1;
     if(dut.cpu.dep_c || dut.cpu.dep_d) j_wait_pair=j_wait_pair+1;
    end
   end
   if((dut.cpu.fetch.consume && dut.cpu.fetch.pop_two)) j_pop2=j_pop2+1;
   if(dut.cpu.commit1) begin
    if(dut.cpu.w_kind==1) j_primary_branch=j_primary_branch+1;
    if(dut.cpu.w1_branch) j_branch=j_branch+1;
    else if(dut.cpu.w1_insn[6:0]==7'h33 && dut.cpu.w1_insn[31:25]==1) j_mul=j_mul+1;
    else j_alu=j_alu+1;
   end
  end
 end
 always @(negedge clk) if(check_secondary) begin
  if(j_branch+j_mul+j_alu!=ref_secondary) $fatal(1,"Slot census mismatch");
  $display("JOINT_WINDOW cross=%0d pop2=%0d primary_branch=%0d branch=%0d mul=%0d alu=%0d dependent_pairs=%0d dependency_split=%0d no_second=%0d",j_cross,j_pop2,j_primary_branch,j_branch,j_mul,j_alu,j_wait_pair,j_dep,j_nosecond);
 end

endmodule
