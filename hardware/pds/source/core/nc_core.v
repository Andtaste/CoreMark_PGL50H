// Isolated limited dual issue: ordered primary + dependency-free ALU sidecar.
// One ledger token per atomic retirement group; dependency IDs include lane.
// Two-entry ID/EX and four-entry EX/MEM boundaries isolate backpressure. An eight-token
// dependency ledger identifies youngest writers (including WAW) and supports
// precise squash. Execution and retirement remain strictly in order.
module nc_core #(parameter ENABLE_BP=1,POST_LOCAL_STORES=0)(input wire clk,rst_n,input wire irq_soft,irq_timer,irq_ext,
 output wire i_req_valid,input wire i_req_ready,output wire[31:0] i_addr,
 input wire i_rsp_valid,output wire i_rsp_ready,input wire[63:0] i_data,input wire i_error,
 output wire d_req_valid,input wire d_req_ready,output wire[31:0] d_addr,d_wdata,
 output wire[31:0] d_write_addr,
 output wire[3:0] d_mask,output wire d_write,
 input wire d_rsp_valid,output wire d_rsp_ready,input wire[31:0] d_rdata,input wire d_error,
 output reg trace_valid,trace_trap,output reg[31:0] trace_pc,trace_insn,trace_data,trace_cause,
 output reg[4:0] trace_rd);
 reg redirect,branch_redirect;reg[31:0] redirect_pc,arch_pc;reg[2:0] redirect_tag;
 reg[4:0] destination1[0:7];
 reg barrier;reg[7:0] live;reg[2:0] head,tail;reg[4:0] destination[0:7];
 wire[3:0] inflight={3'b0,live[0]}+{3'b0,live[1]}+{3'b0,live[2]}+{3'b0,live[3]}+
                    {3'b0,live[4]}+{3'b0,live[5]}+{3'b0,live[6]}+{3'b0,live[7]};
 wire irq_pending;wire[31:0] irq_cause,trap_base,return_pc;wire vector_mode;
 wire irq_take=irq_pending && live==0 && !redirect;
 wire id_mul_hint;wire[9:0] id_pair_flags;wire id_valid,id_fault,id_ready,id_second,pair_issue;wire[31:0] id_pc,id_insn,id_insn1,id_prediction1;
 wire[31:0] id_prediction,ex_prediction;
 reg bp_update_valid,bp_update_branch,bp_update_conditional,bp_update_taken,bp_flush;
 reg[31:0] bp_update_pc,bp_update_target;
 wire wb_valid;wire[279:0] wb_packet;
 wire[2:0] w_tag;wire[31:0] w_pc,w_insn,w_next,w_result,w_address,w_store,w_tval,w_csr;
 wire[4:0] w_cause,w_rd;wire[2:0] w_f3;wire[3:0] w_kind;wire w_wr,w_fault,w_csrwe,w_serial;
 assign {w_tag,w_pc,w_insn,w_next,w_result,w_address,w_store,w_tval,w_csr,w_cause,w_rd,w_f3,w_kind,
         w_wr,w_fault,w_csrwe,w_serial}=wb_packet;
 wire[64:0] w_side;wire commit=wb_valid && !w_fault;
 wire commit1=commit && w_side[64];
 // Under commit1, admitted ALU/MUL opcodes all have bit6=0 and
 // conditional branch has bit6=1. No full opcode decode on the WB control.
 wire w1_branch=w1_insn[6];
 wire w1_wr=!w1_branch;
 wire[31:0] w1_pc=w_next,w1_insn=w_side[63:32],w1_result=w_side[31:0];
 wire[4:0] w1_rd=w1_branch ? 5'b0 : w1_insn[11:7];
 wire do_trap=wb_valid && w_fault;
 wire do_mret=commit && w_kind==8 && w_insn==32'h30200073;
 nc_fetch #(.ENABLE_BP(ENABLE_BP)) fetch(.clk(clk),.rst_n(rst_n),.redirect(redirect),.target(redirect_pc),
  .bp_flush(bp_flush),.bp_update_valid(bp_update_valid),.bp_update_branch(bp_update_branch),
  .bp_update_conditional(bp_update_conditional),.bp_update_taken(bp_update_taken),
  .bp_update_pc(bp_update_pc),.bp_update_target(bp_update_target),.prediction(id_prediction),
  .stop(barrier || irq_pending),.req_valid(i_req_valid),.req_ready(i_req_ready),.req_addr(i_addr),
  .rsp_valid(i_rsp_valid),.rsp_ready(i_rsp_ready),.rsp_data(i_data),.rsp_error(i_error),
  .valid(id_valid),.ready(id_ready),.take_two(pair_issue),.second_valid(id_second),
  .primary_multiply_hint(id_mul_hint),.pair_flags(id_pair_flags),.prediction1(id_prediction1),.inst1(id_insn1),.pc(id_pc),.inst(id_insn),.fault(id_fault));
 wire[3:0] id_kind;wire[31:0] id_imm;wire use1,use2,id_wr,id_serial,id_illegal;
 wire[4:0] rs1,rs2,rd;wire csr_exists,csr_writable;wire[31:0] csr_read,a,b;
 wire[18:0] id_control,ex_control;
 nc_decode decode(.insn(id_insn),.kind(id_kind),.imm(id_imm),.use1(use1),.use2(use2),
  .write_rd(id_wr),.serial(id_serial),.illegal(id_illegal),.rs1(rs1),.rs2(rs2),.rd(rd),
  .csr_exists(csr_exists),.csr_writable(csr_writable),.control(id_control));
 wire[3:0] id1_kind;wire[31:0] id1_imm,c,d;wire id1_use1,id1_use2,id1_wr,id1_serial,id1_illegal;
 wire[4:0] rs1_1,rs2_1,rd1;wire[18:0] id1_control;
 nc_decode decode1(.insn(id_insn1),.kind(id1_kind),.imm(id1_imm),.use1(id1_use1),.use2(id1_use2),
  .write_rd(id1_wr),.serial(id1_serial),.illegal(id1_illegal),.rs1(rs1_1),.rs2(rs2_1),.rd(rd1),
  .csr_exists(1'b0),.csr_writable(1'b0),.control(id1_control));
 nc_regfile rf(.clk(clk),.we(commit && w_wr),.wa(w_rd),.wd(w_result),.ra(rs1),.rb(rs2),.a(a),.b(b),
  .we1(commit1 && w1_wr),.wa1(w1_rd),.wd1(w1_result),.rc(rs1_1),.rd(rs2_1),.c(c),.d(d));
 // Youngest matching live producer wins. This combinational network ends at
 // ID/EX registers; it does not feed a ready chain or EX address calculation.
 reg dep_a,dep_b,dep_c,dep_d,second_dep;reg[3:0] tag_a,tag_b,tag_c,tag_d;
 reg[7:0] match_c,match_c1,match_d,match_d1;reg[15:0] producers_c,producers_d;integer n;reg[7:0] match_a1,match_b1;
 reg[7:0] match_a,match_b,below_tail;reg[15:0] producers_a,producers_b,below_tail16;
 // Encode wrapped and non-wrapped candidates in parallel. Only a narrow
 // three-bit choice follows the tail-side reduction, not an eight-bit
 // eligible mask followed by priority and another encoder.
 // Four-bit encoded identity is retained. Encode interleaved lanes in
 // a balanced tree, rather than encode group then dynamically select lane.
 function [3:0] newest4;
  input[15:0] mask;
  reg[1:0] q0,q1,q2,q3;reg[2:0] lo,hi;
  begin
   q0={|mask[3:2],mask[3] || (!mask[2] && mask[1])};
   q1={|mask[7:6],mask[7] || (!mask[6] && mask[5])};
   q2={|mask[11:10],mask[11] || (!mask[10] && mask[9])};
   q3={|mask[15:14],mask[15] || (!mask[14] && mask[13])};
   lo={|mask[7:4],(|mask[7:4] ? q1 : q0)};
   hi={|mask[15:12],(|mask[15:12] ? q3 : q2)};
   newest4={|mask[15:8],(|mask[15:8] ? hi : lo)};
  end
 endfunction
 always @* begin
  match_a=0;match_b=0;match_a1=0;match_b1=0;below_tail=0;second_dep=0;
  dep_a=0;dep_b=0;dep_c=0;dep_d=0;tag_a=0;tag_b=0;tag_c=0;tag_d=0;
  match_c=0;match_c1=0;match_d=0;match_d1=0;
  // Fixed-slot comparisons avoid rotating/indexing the destination array.
  // The youngest live writer is the highest matching slot below tail, or
  // the highest matching slot overall when the circular interval wrapped.
  // Source-use decode qualifies only the final wait flag, not tag priority.
  for(n=0;n<8;n=n+1) begin
   below_tail[n]=n<{29'b0,tail};
   if(live[n]) begin
    match_a[n]=destination[n]!=0 && destination[n]==rs1;
    match_b[n]=destination[n]!=0 && destination[n]==rs2;
    match_a1[n]=destination1[n]!=0 && destination1[n]==rs1;
    match_b1[n]=destination1[n]!=0 && destination1[n]==rs2;
    match_c[n]=destination[n]!=0 && destination[n]==rs1_1;
    match_d[n]=destination[n]!=0 && destination[n]==rs2_1;
    match_c1[n]=destination1[n]!=0 && destination1[n]==rs1_1;
    match_d1[n]=destination1[n]!=0 && destination1[n]==rs2_1;
   end
  end
  for(n=0;n<8;n=n+1) begin
   producers_a[2*n]=match_a[n];producers_a[2*n+1]=match_a1[n];
   producers_b[2*n]=match_b[n];producers_b[2*n+1]=match_b1[n];
   producers_c[2*n]=match_c[n];producers_c[2*n+1]=match_c1[n];
   producers_d[2*n]=match_d[n];producers_d[2*n+1]=match_d1[n];
   below_tail16[2*n]=below_tail[n];below_tail16[2*n+1]=below_tail[n];
  end
  tag_a=|(producers_a & below_tail16) ? newest4(producers_a & below_tail16) : newest4(producers_a);
  tag_b=|(producers_b & below_tail16) ? newest4(producers_b & below_tail16) : newest4(producers_b);
  dep_a=use1 && |(match_a|match_a1);dep_b=use2 && |(match_b|match_b1);
  tag_c=|(producers_c & below_tail16) ? newest4(producers_c & below_tail16) : newest4(producers_c);
  tag_d=|(producers_d & below_tail16) ? newest4(producers_d & below_tail16) : newest4(producers_d);
  dep_c=id_pair_flags[5] && |(match_c|match_c1);dep_d=id_pair_flags[6] && |(match_d|match_d1);
 end
 wire ex_credit,ex_valid,ex_pop,ex_occupied;wire[203:0] ex_packet;wire[2:0] ex_tag;
 reg f_valid;reg[2:0] f_tag;reg[31:0] f_data;
 reg f1_valid;wire[2:0] f1_tag=f_tag;reg[31:0] f1_data;
 wire m_valid,m_lane;wire[2:0] m_tag;wire[3:0] m_next_tag;wire[2:0] future_w_tag;wire[31:0] m_data;
 wire issue=id_valid && !barrier && !redirect && !do_trap && !irq_pending && ex_credit && !live[tail] &&
             (!(id_serial || id_fault) || live==0);
 // Pair only a clean sequential non-control primary with a plain ALU.
 // Lane1 never waits: any live source producer or intra-pair RAW splits
 // the group. Lane0 therefore always progresses independently of lane1.
 // Static pair legality/source-use flags came through the IF response
 // register boundary. Only live dependency comparisons remain in ID.
 wire extended_pair=id_pair_flags[9] && (id_pair_flags[3] ||
  ((id_kind==4 || id_kind==5) && id_insn1[6])) && !id_prediction[31];
 // Declining a pair leaves its second instruction at the fetch head.
 wire pair_candidate=!(id_mul_hint && (dep_c || dep_d)) && id_second && !id_fault && id_pair_flags[4] &&
  !id_prediction[30] && ((id_pair_flags[8] && !id_prediction1[31]) || (extended_pair && (id_insn1[6] || !id_prediction1[31]))) &&
  !second_dep && !(id_pair_flags[2] && rd!=0 && ((id_pair_flags[5] && rd==rs1_1) || (id_pair_flags[6] && rd==rs2_1))) &&
  !(id_pair_flags[2] && id_pair_flags[7] && rd!=0 && rd==rd1);
 assign pair_issue=issue && pair_candidate;
 assign id_ready=issue;
 wire[223:0] ex_side;
 wire[3:0] id_side_kind=extended_pair ? (id_insn1[6] ? 4'd1 : 4'd6) : 4'd0;
 wire[223:0] id_side={pair_candidate,id1_control,id_side_kind,id_pc+32'd4,id_insn1,c,d,id1_imm,id_prediction1,rd1,id_pair_flags[7],2'b0};
 nc_operands operands(.clk(clk),.rst_n(rst_n),.clear(redirect || do_trap),
  .in_valid(issue),.in_ready(ex_credit),.in_tag(tail),.in_side(id_side),.out_side(ex_side),
  .in_control(id_control),.out_control(ex_control),
  .in_prediction(id_prediction),.out_prediction(ex_prediction),
  .in_packet({id_kind,id_pc,id_insn,a,b,id_imm,csr_read,rd,id_wr,id_illegal,id_fault}),
  .next_f_tag(ex_tag),.next_w_tag(future_w_tag),.next_m_tag(m_next_tag),
  .wait_c(pair_candidate && dep_c),.wait_d(pair_candidate && dep_d),.tag_c(tag_c),.tag_d(tag_d),
  .wait_a(dep_a),.wait_b(dep_b),.tag_a(tag_a),.tag_b(tag_b),
  .f_valid(f_valid),.f_tag({f_tag,1'b0}),.f_data(f_data),
  .f1_valid(f1_valid),.f1_tag({f1_tag,1'b1}),.f1_data(f1_data),
  .w1_valid(commit1 && w1_rd!=0),.w1_tag({w_tag,1'b1}),.w1_data(w1_result),
  .w_valid(commit && w_wr && w_rd!=0),.w_tag({w_tag,1'b0}),.w_data(w_result),
  .m_valid(m_valid),.m_tag({m_tag,m_lane}),.m_data(m_data),
  .out_valid(ex_valid),.out_ready(ex_pop),.out_packet(ex_packet),.out_tag(ex_tag),.occupied(ex_occupied));
 wire execute_valid,execute_ready,mem_credit,mem_valid,memory_ready,memory_done;
 wire[276:0] execute_packet;wire[279:0] mem_packet,memory_packet;
 assign future_w_tag=memory_packet[279:277];
 wire ex_enable=!redirect && !do_trap;
 wire execute_redirect;wire[31:0] execute_target,execute_aux;
 wire prediction_wrong,execute_taken;
 assign ex_pop=execute_ready && ex_enable;
 nc_execute execute(.clk(clk),.rst_n(rst_n),.clear(redirect || do_trap),
  .valid(ex_valid && ex_enable),.ready(execute_ready),.packet(ex_packet),.control(ex_control),
  .redirect_needed(execute_redirect),.redirect_target(execute_target),
  .prediction(ex_prediction),.prediction_wrong(prediction_wrong),.branch_taken(execute_taken),
  .out_valid(execute_valid),.out_ready(mem_credit),.out_packet(execute_packet),.memory_aux(execute_aux));
 wire ex_fire=execute_valid && mem_credit;
 wire[276:0] secondary_result;wire side_wrong,side_taken;wire[31:0] side_target;
 wire side_branch=ex_side[223] && ex_side[203:200]==1;
 wire side_multiply=ex_side[223] && ex_side[203:200]==6;
 wire resolved_branch=ex_branch || side_branch;
 wire[31:0] resolved_prediction=side_branch ? ex_side[39:8] : ex_prediction;
 wire resolved_taken=side_branch ? side_taken : execute_taken;
 wire[31:0] resolved_target=side_branch ? side_target : execute_target;
 // Side admission permits conditional branches, ALU and MUL only.
 // Tie JAL/JALR control off at this boundary, removing unused AGU/target
 // comparisons from the secondary prediction path; no added cycle.
 nc_execute #(.ENABLE_DIV(0)) execute1(.clk(clk),.rst_n(rst_n),.clear(redirect || do_trap),
  .valid(ex_valid && ex_enable && ex_side[223]),.ready(),.packet(ex_side[203:0]),.control({2'b0,ex_side[220:204]}),
  .redirect_needed(),.redirect_target(side_target),.prediction(ex_side[39:8]),.prediction_wrong(side_wrong),.branch_taken(side_taken),
  .out_valid(),.out_ready(mem_credit),.out_packet(secondary_result),.memory_aux());
 wire side_execute=ex_side[223] && !execute_packet[2] && !prediction_wrong;
 wire[31:0] side_value=side_branch ? secondary_result[212:181] : side_multiply ? 32'b0 : secondary_result[180:149];
 wire[64:0] side_result={side_execute,secondary_result[244:213],side_value};
 always @(posedge clk) if(ex_fire) begin f1_data<=secondary_result[180:149];end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) f1_valid<=0;else f1_valid<=ex_fire && side_execute && !side_branch && !side_multiply && secondary_result[15:11]!=0;
 end
 wire ex_multiply=execute_packet[7:4]==6 && !execute_packet[10] && !execute_packet[2];
 wire[2:0] mul_query_tag;wire mul_query_ready,mul_consume,mul_busy;wire[31:0] mul_query_data;
 // This trial also admits a side MUL with a primary LSU transaction.
 // Primary faults suppress side retirement; a trap clears speculative MUL state.
 // Original note: A side MUL is admitted only with a legal ordinary ALU primary,
 // clean fetch, and no primary prediction. It cannot have a primary EX
 // fault/misprediction, so do not send that late comparison into DSP CE.
 wire mul_accept=ex_fire && (ex_multiply || side_multiply);
 wire[31:0] mul_a=side_multiply ? ex_side[135:104] : ex_packet[135:104];
 wire[31:0] mul_b=side_multiply ? ex_side[103:72] : ex_packet[103:72];
 wire[1:0] mul_op=side_multiply ? ex_side[149:148] : ex_packet[149:148];
 nc_mul_pipeline multiply(.clk(clk),.rst_n(rst_n),.clear(do_trap),.accept(mul_accept),
  .in_tag(ex_tag),.in_lane(side_multiply),.forward_lane(m_lane),.operation(mul_op),.a(mul_a),.b(mul_b),
  .next_forward_tag(m_next_tag),.query_tag(mul_query_tag),.consume(mul_consume),.query_ready(mul_query_ready),.query_data(mul_query_data),
  .forward_valid(m_valid),.forward_tag(m_tag),.forward_data(m_data),.busy(mul_busy));
 wire ex_branch=execute_packet[7:4]>=1 && execute_packet[7:4]<=3;
 // Only incorrect predicted next-PC requires recovery, including stale
 // taken predictions on non-branches. Correction crosses a register to IF.
 wire branch_event=ex_fire && (prediction_wrong || (side_branch && !execute_packet[2] && side_wrong));
 always @(posedge clk) begin
  bp_update_pc<=side_branch ? secondary_result[276:245] : execute_packet[276:245];bp_update_target<=resolved_target;
  bp_update_branch<=resolved_branch;bp_update_conditional<=side_branch || execute_packet[7:4]==1;
  bp_update_taken<=resolved_taken;
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin bp_update_valid<=0;bp_flush<=0;end
  else begin
   bp_update_valid<=ENABLE_BP && ex_fire && !execute_packet[2] && (resolved_branch || ex_prediction[31]);
   bp_flush<=commit && w_kind==9;
  end
 end
 // Secondary PC equals primary sequential next-PC; rd comes from its instruction.
 // This removes 37 stored bits without an extra EX adder or any new bypass.
 // Compact only mutually exclusive fields at the EX/MEM register boundary.
 // A store does not need an ALU result. Memory addresses, CSR new values and
 // synchronous trap values belong to distinct classes. Qualification uses
 // registered EX class/illegal/fetch bits, never a late branch-fault mux.
 wire queue_store=ex_packet[203:200]==5;
 wire[31:0] queue_value=queue_store ? execute_packet[116:85] : execute_packet[180:149];
 wire[31:0] queue_aux=execute_aux;
 wire[183:0] compact_packet;wire[64:0] compact_side,memory_side;
 wire queued_valid,queue_credit;wire[248:0] queued_packet;
 wire[248:0] incoming_packet={side_result,ex_tag,execute_packet[276:181],queue_value,queue_aux,execute_packet[20:0]};
 // Input credit is still registered occupancy. Empty queue hands EX to the
 // MEM slot on the same edge; blocked instructions enter the existing FIFO.
 assign mem_credit=queue_credit;
 assign mem_valid=queued_valid || execute_valid;
 assign {compact_side,compact_packet}=queued_valid ? queued_packet : incoming_packet;
 wire direct_take=!queued_valid && execute_valid && memory_ready;
 // Separate request address from the compact auxiliary field. Branch next-PC
 // is a valid auxiliary value, but must not drive the early load address cone.
 wire[31:0] direct_agu=ex_packet[135:104]+ex_packet[71:40];
 wire[31:0] launch_address=queued_valid ? compact_packet[52:21] : direct_agu;

 nc_fifo #(.WIDTH(249),.DEPTH(4)) memory_queue(.clk(clk),.rst_n(rst_n),.clear(do_trap),
  .in_valid(execute_valid && !direct_take),.in_ready(queue_credit),
  .in_data(incoming_packet),
  .out_valid(queued_valid),.out_ready(memory_ready),.out_data(queued_packet));
 wire[31:0] compact_value=compact_packet[84:53],compact_aux=compact_packet[52:21];
 wire compact_store=compact_packet[7:4]==5;
 assign mem_packet={compact_packet[183:85],(compact_store ? 32'b0 : compact_value),compact_aux,
                    (compact_store ? compact_value : 32'b0),(compact_packet[2] ? compact_aux : 32'b0),
                    (compact_packet[7:4]==7 && !compact_packet[2] ? compact_aux : 32'b0),compact_packet[20:0]};
 nc_memory #(.EARLY_REQUEST(1),.POST_LOCAL_STORES(POST_LOCAL_STORES)) memory(.side_packet(compact_side),.wb_side(memory_side),.clk(clk),.rst_n(rst_n),.kill(do_trap),.valid(mem_valid),.ready(memory_ready),.packet(mem_packet),.launch_address(launch_address),.write_address(d_write_addr),
  .mul_tag(mul_query_tag),.mul_ready(mul_query_ready),.mul_data(mul_query_data),.mul_consume(mul_consume),
  .wb_valid(memory_done),.wb_packet(memory_packet),
  .req_valid(d_req_valid),.req_ready(d_req_ready),.req_addr(d_addr),.req_data(d_wdata),
  .req_mask(d_mask),.req_write(d_write),.rsp_valid(d_rsp_valid),.rsp_ready(d_rsp_ready),
  .rsp_data(d_rdata),.rsp_error(d_error));
 reg[64:0] wb_side_q;assign w_side=wb_side_q;
 reg wb_v;reg[279:0] wb_q;assign wb_valid=wb_v;assign wb_packet=wb_q;
 always @(posedge clk) if(memory_done) begin wb_q<=memory_packet;wb_side_q<=memory_side;end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) wb_v<=0;else wb_v<=memory_done;
 end
 always @(posedge clk) if(ex_fire) begin f_tag<=ex_tag;f_data<=execute_packet[180:149];end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) f_valid<=0;
  else f_valid<=ex_fire && !execute_packet[2] && execute_packet[3] && execute_packet[15:11]!=0 &&
                execute_packet[7:4]!=4 && !ex_multiply;
 end
 nc_csr csr(.clk(clk),.rst_n(rst_n),.retire(commit),.retire1(commit1),.raddr(id_insn[31:20]),
  .stats_events({
   (id_valid && !issue),                            // 7ce: ID blocked cycles
   (ex_occupied && !ex_valid),                      // 7cd: operand wait cycles
   (commit && w_kind==5),                           // 7cc: retired stores
   (commit && w_kind==4),                           // 7cb: retired loads
   commit1,commit,1'b0,                               // 7ca secondary, 7c9 retire, 7c8 overflow
   ((commit && w_kind>=1 && w_kind<=3) || (commit1 && w1_branch)),branch_event,  // 7c7 BJP retired, 7c6 redirects
   (ex_valid && ex_packet[203:200]==6 && !execute_valid && ex_enable),
   (!memory_ready && !do_trap),                     // 7c4: MEM transaction occupied
   (!id_valid),                                    // 7c3: fetch output empty
   (i_req_valid && !i_req_ready),1'b1}),             // 7c2 IF request wait, 7c1 cycles
  .rdata(csr_read),.exists(csr_exists),.writable(csr_writable),
  .we(commit && w_csrwe),.waddr(w_insn[31:20]),.wdata(w_csr),
  .trap(do_trap || irq_take),.mret(do_mret),.trap_pc(irq_take ? arch_pc : w_pc),
  .trap_cause(irq_take ? irq_cause : {27'b0,w_cause}),.trap_value(irq_take ? 32'b0 : w_tval),
  .irq_soft(irq_soft),.irq_timer(irq_timer),.irq_ext(irq_ext),
  .irq_pending(irq_pending),.irq_cause(irq_cause),.trap_base(trap_base),.return_pc(return_pc),.vector_mode(vector_mode));
 // Secondary trace follows primary trace on the same cycle, never a
 // separate architectural transaction that could pass a primary fault.
 reg trace1_valid;reg[31:0] trace1_pc,trace1_insn,trace1_data;reg[4:0] trace1_rd;
 always @(posedge clk) begin
  trace1_pc<=w1_pc;trace1_insn<=w1_insn;trace1_rd<=w1_rd;trace1_data<=w1_rd!=0 ? w1_result : 0;
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) trace1_valid<=0;else trace1_valid<=commit1;
 end
 integer r;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   live<=0;head<=0;tail<=0;barrier<=0;redirect<=0;branch_redirect<=0;redirect_tag<=0;redirect_pc<=0;arch_pc<=0;
   trace_valid<=0;trace_trap<=0;trace_pc<=0;trace_insn<=0;trace_data<=0;trace_rd<=0;trace_cause<=0;
   for(r=0;r<8;r=r+1) begin destination[r]<=0;destination1[r]<=0;end
  end else begin
   redirect<=0;branch_redirect<=0;
   // Target data is prewritten every cycle. Only the narrow valid/tag
   // controls depend on branch resolution; no 32-bit branch-event CE.
   redirect_pc<=side_branch ? secondary_result[212:181] : execute_packet[212:181];
   // The registered branch_redirect qualifies this token next cycle.
   // Prewrite the three data bits so late prediction comparison does not
   // also drive a token CE with its larger setup requirement.
   redirect_tag<=ex_tag;
   trace_valid<=wb_valid || irq_take;trace_trap<=do_trap || irq_take;
   if(wb_valid || irq_take) begin
    trace_pc<=irq_take ? arch_pc : w_pc;trace_insn<=irq_take ? 0 : w_insn;
    trace_rd<=commit && w_wr ? w_rd : 0;trace_data<=commit && w_wr && w_rd!=0 ? w_result : 0;
    trace_cause<=irq_take ? irq_cause : do_trap ? {27'b0,w_cause} : 0;
   end
   if(wb_valid) begin live[w_tag]<=0;head<=w_tag+1'b1;end
   if(issue) begin live[tail]<=1;destination[tail]<=id_wr ? rd : 0;destination1[tail]<=pair_candidate && id_pair_flags[7] ? rd1 : 0;tail<=tail+1'b1;end
   if(issue && (id_serial || id_fault)) barrier<=1;
   if(wb_valid && w_serial) barrier<=0;
   if(branch_redirect) begin
    // Primary branch may annul a speculatively admitted ALU side while the
    // retirement group remains live. Its destination is no longer a producer.
    // Correct-path ID is blocked during redirect, so it sees this cancellation.
    destination1[redirect_tag]<=0;
    for(r=0;r<8;r=r+1) if(((r-head)&7)>((redirect_tag-head)&7)) live[r]<=0;
    tail<=redirect_tag+1'b1;
   end
   if(commit) arch_pc<=do_mret ? return_pc : commit1 ? (w1_branch ? w1_result : w1_pc+32'd4) : w_next;
   if(branch_event) begin redirect<=1;branch_redirect<=1;end
   if(commit && (w_kind==9 || do_mret)) begin redirect<=1;redirect_pc<=do_mret ? return_pc : w_next;end
   if(do_trap || irq_take) begin
    live<=0;head<=0;tail<=0;barrier<=0;redirect<=1;branch_redirect<=0;
    redirect_pc<=trap_base + (irq_take && vector_mode ? {25'b0,irq_cause[4:0],2'b0} : 0);
    arch_pc<=trap_base + (irq_take && vector_mode ? {25'b0,irq_cause[4:0],2'b0} : 0);
   end
  end
 end
endmodule
