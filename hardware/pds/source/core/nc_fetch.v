// Eight-word sliding instruction FIFO, two parity banks and two cached heads.
// Two disjoint PC[2] BTB banks preserve the original 64-entry capacity.
// No request acceptance or consumer pop feeds input credit combinationally.
module nc_fetch #(parameter ENABLE_BP=1)(input wire clk,rst_n,redirect,stop,input wire[31:0] target,
 input wire bp_flush,bp_update_valid,bp_update_branch,bp_update_conditional,bp_update_taken,
 input wire[31:0] bp_update_pc,bp_update_target,output wire[31:0] prediction,prediction1,
 output wire req_valid,input wire req_ready,output wire[31:0] req_addr,
 input wire rsp_valid,output wire rsp_ready,input wire[63:0] rsp_data,input wire rsp_error,
 output wire[9:0] pair_flags,
 output wire valid,input wire ready,input wire take_two,output wire second_valid,
 output wire[31:0] pc,inst,inst1,output wire fault);
 reg[31:0] next_pc,cmd_pc,flight_pc,cmd_prediction,flight_prediction,cmd_prediction1,flight_prediction1;
 reg cmd_two,flight_two,cmd_valid,cmd_stale,flight,flight_stale;
 wire[31:0] lookup_prediction,lookup_prediction1;
 wire[31:0] even_prediction,odd_prediction;
 wire[31:0] even_pc={next_pc[31:3],3'b000},odd_pc={next_pc[31:3],3'b100};
 generate if(ENABLE_BP) begin:predictor
  nc_btb_bank btb(.clk(clk),.rst_n(rst_n),.flush(bp_flush),.lookup_pc(even_pc),.prediction(even_prediction),
   .update_valid(bp_update_valid && !bp_update_pc[2]),.update_branch(bp_update_branch),.update_conditional(bp_update_conditional),
   .update_taken(bp_update_taken),.update_pc(bp_update_pc),.update_target(bp_update_target));
  nc_btb_bank btb1(.clk(clk),.rst_n(rst_n),.flush(bp_flush),.lookup_pc(odd_pc),.prediction(odd_prediction),
   .update_valid(bp_update_valid && bp_update_pc[2]),.update_branch(bp_update_branch),.update_conditional(bp_update_conditional),
   .update_taken(bp_update_taken),.update_pc(bp_update_pc),.update_target(bp_update_target));
 assign lookup_prediction=next_pc[2] ? odd_prediction : even_prediction;
  assign lookup_prediction1=odd_prediction;
 end else begin:no_predictor
  assign lookup_prediction=0;assign lookup_prediction1=0;
 end endgenerate
 function[8:0] classify_parts;
  input[31:0] insn;
  reg[6:0] op,f7;reg[2:0] f3;
  reg upper,imm_op,reg_op,zero_f7,alt_f7;
  reg base_alu,zero_alu,alt_alu,memory_op,multiply_op;
  begin
   op=insn[6:0];f3=insn[14:12];f7=insn[31:25];
   upper=(op & 7'h5f)==7'h17;
   imm_op=op==7'h13;reg_op=op==7'h33;
   zero_f7=f7==0;alt_f7=f7==7'h20;
   // Non-shift immediates do not interpret upper immediate bits as f7.
   base_alu=upper || (imm_op && (f3[1] || !f3[0]));
   zero_alu=(imm_op || reg_op) && zero_f7;
   alt_alu=alt_f7 && ((imm_op && f3==5) || (reg_op && (f3==0 || f3==5)));
   memory_op=(op==7'h03 && (!f3[1] || f3==2)) ||
             (op==7'h23 && !f3[2] && f3[1:0]!=3);
   multiply_op=reg_op && f7==1 && !f3[2];
   classify_parts={((1 && op==7'h63 && f3!=2 && f3!=3 && !insn[8]) || (1 && multiply_op)),multiply_op,memory_op,alt_alu,zero_alu,base_alu,
                   op!=7'h23 && op!=7'h63,reg_op || op==7'h63,imm_op || reg_op || op==7'h63};
  end
 endfunction
 function[4:0] pack_flags;
  input[8:0] parts;
  begin pack_flags={|parts[8:3],|parts[5:3],parts[2:0]};end
 endfunction
 // Simulation observability only; synthesized incoming data uses parts.
 function[4:0] classify;
  input[31:0] insn;
  begin classify=pack_flags(classify_parts(insn));end
 endfunction
 function[4:0] classify_side;
  input[31:0] insn;reg[8:0] p;reg[4:0] f;
  begin p=classify_parts(insn);f=pack_flags(p);classify_side={p[8],f[3:0]};end
 endfunction
 // Eight individual instructions, stored in two parity banks. Each bank
 // has one write and one read; no take_two-dependent RAM read address.
 reg[31:0] even_inst[0:3],odd_inst[0:3] /* synthesis syn_ramstyle="lut_ram" */;
 reg[74:0] even_meta[0:3],odd_meta[0:3] /* synthesis syn_ramstyle="registers" */;
 reg[106:0] head_0,head_1;
 reg[2:0] rd,wr;reg[3:0] count;
 reg cmd_link,flight_link,stream_tail_sequential;
 wire response=flight && rsp_valid;
 assign req_valid=cmd_valid && (!flight || response);assign req_addr=cmd_pc;assign rsp_ready=flight;
 wire launch=req_valid && req_ready;
 // Credit is based only on registered words/reservations. Prepare reserves
 // the worst-case two words without using ID pop or downstream ready.
 wire[3:0] reserved=count+(flight ? (flight_two ? 4'd2 : 4'd1) : 4'd0)+
                         (cmd_valid ? (cmd_two ? 4'd2 : 4'd1) : 4'd0);
 wire prepare=(!cmd_valid || launch) && reserved<=6 && !stop && !redirect;
 wire push=response && !flight_stale && !redirect;
 wire[3:0] push_words=push ? (flight_two ? 4'd2 : 4'd1) : 4'd0;
 wire consume=valid && ready;
 wire pop_two=second_valid && take_two;
 wire[3:0] pop_words=consume ? (pop_two ? 4'd2 : 4'd1) : 4'd0;
 wire[2:0] rd_one=rd+3'd1,rd_two=rd+3'd2;
 wire prepare_two=!next_pc[2] && !lookup_prediction[30] && !next_pc[1] && !next_pc[0];
 wire prepared_seq0=!lookup_prediction[30] || {lookup_prediction[29:0],2'b0}==next_pc+32'd4;
 wire prepared_seq1=!lookup_prediction1[30] || {lookup_prediction1[29:0],2'b0}==next_pc+32'd8;
 wire[31:0] in_inst0=flight_pc[2] ? rsp_data[63:32] : rsp_data[31:0];
 // PC, prediction, partial class, fault, adjacency, instruction.
 wire[106:0] in0={flight_pc,flight_prediction,classify_parts(in_inst0),rsp_error,flight_link,in_inst0};
 wire[106:0] in1={flight_pc+32'd4,flight_prediction1,classify_parts(rsp_data[63:32]),rsp_error,1'b1,rsp_data[63:32]};
 wire even_write=push && (!wr[0] || flight_two),odd_write=push && (wr[0] || flight_two);
 wire[1:0] even_write_row=wr[2:1]+{1'b0,wr[0]},odd_write_row=wr[2:1];
 wire[106:0] even_input=wr[0] ? in1 : in0,odd_input=wr[0] ? in0 : in1;
 wire[1:0] even_read_row=rd[2:1]+(rd[0] ? 2'd2 : 2'd1),odd_read_row=rd[2:1]+2'd1;
 wire[106:0] er={even_meta[even_read_row],even_inst[even_read_row]};
 wire[106:0] orv={odd_meta[odd_read_row],odd_inst[odd_read_row]};
 wire[106:0] word2=rd[0] ? orv : er,word3=rd[0] ? er : orv;
 assign valid=count!=0;
 assign pc=head_0[106:75];assign prediction=head_0[74:43];assign fault=head_0[33];assign inst=head_0[31:0];
 assign prediction1=head_1[74:43];assign inst1=head_1[31:0];
 assign second_valid=count>=2 && head_1[32] && !head_1[33] && !prediction[30];
 wire[4:0] side_flags=pack_flags(head_1[42:34]);
 assign pair_flags={head_1[42],side_flags[3:0],pack_flags(head_0[42:34])};
 // Candidate states after consuming one/two words are prepared in parallel.
 // The final take_two choice is a data mux into head FFs, not a RAM address.
 wire[106:0] after_one_0=count>1 ? head_1 : push ? in0 : 107'b0;
 wire[106:0] after_one_1=count>2 ? word2 : count==2 ? (push ? in0 : 107'b0) : push && flight_two ? in1 : 107'b0;
 wire[106:0] after_two_0=count>2 ? word2 : push ? in0 : 107'b0;
 wire[106:0] after_two_1=count>3 ? word3 : count==3 ? (push ? in0 : 107'b0) : push && flight_two ? in1 : 107'b0;
 always @(posedge clk) begin
  if(even_write) begin even_inst[even_write_row]<=even_input[31:0];even_meta[even_write_row]<=even_input[106:32];end
  if(odd_write) begin odd_inst[odd_write_row]<=odd_input[31:0];odd_meta[odd_write_row]<=odd_input[106:32];end
  if(consume) begin
   head_0<=pop_two ? after_two_0 : after_one_0;
   head_1<=pop_two ? after_two_1 : after_one_1;
  end else if(push && count<2) begin
   head_0<=count==0 ? in0 : head_0;
   head_1<=count==0 ? (flight_two ? in1 : 107'b0) : in0;
  end
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   next_pc<=0;cmd_pc<=0;flight_pc<=0;cmd_valid<=0;cmd_stale<=0;flight<=0;flight_stale<=0;
   cmd_prediction<=0;flight_prediction<=0;cmd_prediction1<=0;flight_prediction1<=0;
   cmd_two<=0;flight_two<=0;rd<=0;wr<=0;count<=0;cmd_link<=0;flight_link<=0;stream_tail_sequential<=0;
  end else begin
   if(launch) begin
    cmd_valid<=0;flight<=1;flight_pc<=cmd_pc;flight_prediction<=cmd_prediction;
    flight_prediction1<=cmd_prediction1;flight_two<=cmd_two;flight_link<=cmd_link;flight_stale<=cmd_stale || redirect;
   end else if(response) flight<=0;
   if(prepare) begin
    cmd_valid<=1;cmd_pc<=next_pc;cmd_prediction<=lookup_prediction;cmd_prediction1<=lookup_prediction1;
    cmd_two<=prepare_two;cmd_stale<=0;cmd_link<=stream_tail_sequential;
    stream_tail_sequential<=prepare_two ? prepared_seq1 : prepared_seq0;
    next_pc<=lookup_prediction[30] ? {lookup_prediction[29:0],2'b0} :
      prepare_two && lookup_prediction1[30] ? {lookup_prediction1[29:0],2'b0} : next_pc+(prepare_two ? 32'd8 : 32'd4);
   end
   if(push) wr<=wr+(flight_two ? 3'd2 : 3'd1);
   if(consume) rd<=pop_two ? rd_two : rd_one;
   count<=count+push_words-pop_words;
   if(redirect) begin
    rd<=0;wr<=0;count<=0;next_pc<=target;stream_tail_sequential<=0;
    if(cmd_valid && !launch) cmd_stale<=1;
    else begin
     cmd_valid<=1;cmd_pc<=target;cmd_prediction<=0;cmd_prediction1<=0;cmd_stale<=0;
     cmd_two<=!target[2] && !target[1] && !target[0];cmd_link<=0;stream_tail_sequential<=1;
     next_pc<=target+((!target[2] && !target[1] && !target[0]) ? 32'd8 : 32'd4);
    end
    if(flight && !launch) flight_stale<=1;
   end
  end
 end
endmodule
