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
   if(dut.cpu.mem_valid && dut.cpu.memory.input_multiply && !dut.cpu.memory.state &&
      !dut.cpu.mul_query_ready) mul_head_wait=mul_head_wait+1;
   if(dut.cpu.ex_fire && !dut.cpu.ex_multiply && dut.cpu.mul_busy) mul_overlapped=mul_overlapped+1;
   if(dut.cpu.mul_accept && dut.cpu.memory.state) mul_memory_overlap=mul_memory_overlap+1;
   if(bp_recovering && !dut.cpu.id_valid) bp_recovery_empty=bp_recovery_empty+1;
   if(dut.cpu.branch_event) bp_recovering=1;
   else if(dut.cpu.id_valid && !dut.cpu.redirect) bp_recovering=0;
   if(dut.cpu.ex_fire && !dut.cpu.execute_packet[2]) begin
    if(dut.cpu.ex_branch) begin
     bp_resolved=bp_resolved+1;
     if(dut.cpu.ex_prediction[31]) bp_hits=bp_hits+1;
     if(dut.cpu.ex_prediction[30]) bp_taken=bp_taken+1;
     if(dut.cpu.ex_prediction[30]!=dut.cpu.execute_taken) bp_direction_wrong=bp_direction_wrong+1;
     if(dut.cpu.ex_prediction[30] && dut.cpu.execute_taken &&
        {dut.cpu.ex_prediction[29:0],2'b0}!=dut.cpu.execute_target) bp_target_wrong=bp_target_wrong+1;
     if(dut.cpu.branch_event) bp_wrong=bp_wrong+1;
    end else if(dut.cpu.branch_event) bp_nonbranch_wrong=bp_nonbranch_wrong+1;
   end
   if(dut.cpu.commit) begin
    ref_retired=ref_retired+1;
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
 reg[1023:0] tracefile,uartfile;
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
  if(dut.cpu.m_valid && dut.cpu.commit && dut.cpu.w_wr && dut.cpu.w_rd!=0 &&
     dut.cpu.m_tag==dut.cpu.w_tag && dut.cpu.m_data!==dut.cpu.w_result)
   $fatal(1,"MUL/WB duplicate tag has different values");
  if(dut.cpu.f_valid && dut.cpu.commit && dut.cpu.w_wr && dut.cpu.w_rd!=0 &&
     dut.cpu.f_tag==dut.cpu.w_tag && dut.cpu.f_data!==dut.cpu.w_result)
   $fatal(1,"EX/WB duplicate tag has different values");
  if(dut.cpu.f_valid && dut.cpu.m_valid && dut.cpu.f_tag==dut.cpu.m_tag &&
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

 integer pw[0:41];integer pt[0:7];integer pi;reg pl,pm,po,pa,pj,pd,pac;reg[7:0] pdone=0;
 wire late_a=dut.cpu.dep_a && pt[dut.cpu.tag_a]==0 && pdone[dut.cpu.tag_a] &&
             !(dut.cpu.f_valid && dut.cpu.f_tag==dut.cpu.tag_a) &&
             !(dut.cpu.commit && dut.cpu.w_wr && dut.cpu.w_rd!=0 && dut.cpu.w_tag==dut.cpu.tag_a);
 wire late_b=dut.cpu.dep_b && pt[dut.cpu.tag_b]==0 && pdone[dut.cpu.tag_b] &&
             !(dut.cpu.f_valid && dut.cpu.f_tag==dut.cpu.tag_b) &&
             !(dut.cpu.commit && dut.cpu.w_wr && dut.cpu.w_rd!=0 && dut.cpu.w_tag==dut.cpu.tag_b);
 task classify_dep(input integer token);
  begin
   if(pt[token]==4) pl=1;
   else if(pt[token]==6) pm=1;
   else begin po=1;if(pt[token]==0) begin pa=1;if(pdone[token]) pac=1;end
    else if(pt[token]==2 || pt[token]==3) pj=1;else pd=1;end
  end
 endtask
 initial begin for(pi=0;pi<42;pi=pi+1) pw[pi]=0;for(pi=0;pi<8;pi=pi+1) pt[pi]=0;end
 always @(posedge clk) if(rst_n) begin
  if(dut.cpu.csr.stats.control && dut.cpu.csr.stats.control_data[1]) begin
   for(pi=0;pi<42;pi=pi+1) pw[pi]=0;
  end else if(!dut.cpu.csr.stats.control && dut.cpu.csr.stats.enabled) begin
   pw[0]=pw[0]+1;
   if(dut.cpu.ex_fire) pw[1]=pw[1]+1;
   else if(dut.cpu.redirect || dut.cpu.do_trap) pw[2]=pw[2]+1;
   else if(dut.cpu.ex_occupied && !dut.cpu.ex_valid) pw[3]=pw[3]+1;
   else if(dut.cpu.ex_valid && !dut.cpu.mem_credit) pw[4]=pw[4]+1;
   else if(dut.cpu.ex_valid && !dut.cpu.execute_valid) pw[5]=pw[5]+1;
   else pw[6]=pw[6]+1;
   if(dut.cpu.ex_occupied && !dut.cpu.ex_valid) begin
    pl=0;pm=0;po=0;pa=0;pj=0;pd=0;pac=0;
    if(!dut.cpu.operands.available_a[dut.cpu.operands.rd]) classify_dep(dut.cpu.operands.dep_a[dut.cpu.operands.rd]);
    if(!dut.cpu.operands.available_b[dut.cpu.operands.rd]) classify_dep(dut.cpu.operands.dep_b[dut.cpu.operands.rd]);
    if(pl && !pm && !po) pw[7]=pw[7]+1;
    else if(pm && !pl && !po) pw[8]=pw[8]+1;
    else if(pl && pm && !po) pw[9]=pw[9]+1;
    else begin
     pw[10]=pw[10]+1;
     if(pa) pw[33]=pw[33]+1;if(pj) pw[34]=pw[34]+1;if(pd) pw[35]=pw[35]+1;
     if(pac) pw[36]=pw[36]+1;
    end
   end
   if(dut.cpu.id_valid && !dut.cpu.issue) begin
    if(dut.cpu.redirect || dut.cpu.do_trap) pw[11]=pw[11]+1;
    else if(dut.cpu.barrier) pw[12]=pw[12]+1;
    else if(dut.cpu.irq_pending) pw[13]=pw[13]+1;
    else if(!dut.cpu.ex_credit) pw[14]=pw[14]+1;
    else if(dut.cpu.live[dut.cpu.tail]) pw[15]=pw[15]+1;
    else if((dut.cpu.id_serial || dut.cpu.id_fault) && dut.cpu.live!=0) pw[16]=pw[16]+1;
    else pw[17]=pw[17]+1;
   end
   if(dut.cpu.id_valid && !dut.cpu.ex_credit && dut.cpu.ex_valid && dut.cpu.ex_pop &&
      !dut.cpu.redirect && !dut.cpu.do_trap) pw[18]=pw[18]+1;
   if(dut.cpu.execute_valid && !dut.cpu.mem_credit && dut.cpu.mem_valid && dut.cpu.memory_ready &&
      !dut.cpu.redirect && !dut.cpu.do_trap) pw[19]=pw[19]+1;
   if(dut.cpu.memory.memory_pending) pw[20]=pw[20]+1;
   if(dut.cpu.d_req_valid && !dut.cpu.d_req_ready) pw[21]=pw[21]+1;
   if(dut.cpu.mem_valid && dut.cpu.memory.input_multiply && !dut.cpu.memory.state && !dut.cpu.mul_query_ready) pw[22]=pw[22]+1;
   if(dut.cpu.d_req_valid && dut.cpu.d_req_ready) pw[23]=pw[23]+1;
   if(dut.cpu.d_rsp_valid && dut.cpu.d_rsp_ready) pw[24]=pw[24]+1;
   pw[25+int'(dut.cpu.memory_queue.count)]=pw[25+int'(dut.cpu.memory_queue.count)]+1;
   if(dut.cpu.operands.count==3) pw[38]=pw[38]+1;
   else pw[30+int'(dut.cpu.operands.count)]=pw[30+int'(dut.cpu.operands.count)]+1;
   if(dut.cpu.issue && (late_a || late_b)) pw[37]=pw[37]+1;
   if(dut.cpu.d_req_valid && dut.cpu.d_req_ready && dut.cpu.memory.memory_pending) pw[39]=pw[39]+1;
   if(dut.cpu.memory.buffered) pw[40]=pw[40]+1;
   if(dut.cpu.memory.turnover && dut.cpu.mem_valid && dut.cpu.memory_ready && !dut.cpu.memory.input_memory) pw[41]=pw[41]+1;
  end
  if(dut.cpu.ex_fire && !dut.cpu.execute_packet[2] && dut.cpu.execute_packet[7:4]==0) pdone[dut.cpu.ex_tag]=1;
  if(dut.cpu.issue) begin
   pt[dut.cpu.tail]=(dut.cpu.id_kind==6 && dut.cpu.id_insn[14]) ? 7 : int'(dut.cpu.id_kind);
   pdone[dut.cpu.tail]=0;
  end
 end
 always @(negedge clk) if(check_stats) begin
  for(pi=0;pi<42;pi=pi+1) $display("WAIT_PROFILE %0d %0d",pi,pw[pi]);
 end

endmodule
