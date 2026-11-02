// Uniform MEM register owns every group. The spill FIFO is optional when empty.
// Local requests may launch at the EX/MEM ownership edge; MMIO starts in MEM.
// Bus response and load formatting terminate at existing registered WB only.
module nc_memory #(parameter ENABLE_L0_CACHE=0,EARLY_REQUEST=0,POST_LOCAL_STORES=0,USE_SEPARATE_LOAD_ADDRESS=0)(input wire clk,rst_n,kill,input wire valid,output wire ready,
 input wire l0_hit,output wire l0_fill_valid,output wire[31:0] l0_fill_address,l0_fill_word,
 input wire[64:0] side_packet,output wire[64:0] wb_side,
 input wire[31:0] load_address,launch_address,output wire[31:0] write_address,input wire[279:0] packet,output wire wb_valid,output wire[279:0] wb_packet,
 output wire[2:0] mul_tag,input wire mul_ready,input wire[31:0] mul_data,output wire mul_consume,
 output wire req_valid,input wire req_ready,output wire[31:0] req_addr,req_data,
 output wire[3:0] req_mask,output wire req_write,
 input wire rsp_valid,output wire rsp_ready,input wire[31:0] rsp_data,input wire rsp_error);
 localparam IDLE=2'd0,MEMORY=2'd1,BUFFERED=2'd2;
 reg posted_response;
 reg slot_valid,sent,held_l0_hit;reg[279:0] held;reg[64:0] held_side;
 wire[31:0] pc,insn,next_pc,result,address,store_data,tval,csr_data;
 wire[4:0] cause,rd;wire[2:0] f3,tag;wire[3:0] kind;wire wr,exception,csr_we,serial;
 assign {tag,pc,insn,next_pc,result,address,store_data,tval,csr_data,cause,rd,f3,kind,wr,exception,csr_we,serial}=held;
 wire memory_access=!exception && !held_l0_hit && (kind==4 || kind==5);
 wire primary_multiply=!exception && kind==6 && !f3[2];
 wire secondary_multiply=!exception && held_side[64] && !held_side[38] && held_side[37] && !held_side[34] && held_side[57];
 wire multiply_access=primary_multiply || secondary_multiply;
 wire memory_pending=slot_valid && memory_access,buffered=slot_valid && !memory_access;
 wire[1:0] state=!slot_valid ? IDLE : memory_access ? MEMORY : BUFFERED;
 // A previous fast-completed local write owns this response, even if a
 // new ALU/load/store has already entered the ordered MEM slot.
 wire response=memory_pending && sent && rsp_valid && !posted_response;
 wire response_error=response && rsp_error;
 assign l0_fill_valid=ENABLE_L0_CACHE && response && kind==4 && !exception && !response_error && !kill;
 assign l0_fill_address=address;assign l0_fill_word=rsp_data;
 wire local_write_address=address<32'h00010000 || (address>=32'h10000000 && address<32'h10008000);
 wire store_fast=POST_LOCAL_STORES && memory_pending && kind==5 && local_write_address;
 wire posted_fire=!kill && store_fast && old_request && req_ready;
 wire complete=slot_valid && (!memory_access || response || posted_fire) && (!multiply_access || mul_ready);
 wire can_accept=!kill && (!slot_valid || (complete && !exception && !response_error));
 assign ready=can_accept;
 wire start=valid && ready;
 wire input_memory=!packet[2] && !(ENABLE_L0_CACHE && l0_hit) && (packet[7:4]==4 || packet[7:4]==5);
 wire[31:0] input_address=USE_SEPARATE_LOAD_ADDRESS ? load_address : packet[148:117];
 wire input_local=launch_address<32'h00010000 || (launch_address>=32'h10000000 && launch_address<32'h10008000);
 // At most one detached response. It may be replaced only as its real
 // response is drained; no assumption of always-ready or one-cycle buses.
 wire response_credit=!posted_response || rsp_valid;
 wire old_request=memory_pending && !sent && response_credit;
 wire early_request=EARLY_REQUEST && can_accept && valid && input_memory && packet[7:4]==4 && input_local && !old_request && response_credit;
 // Ownership, rather than request valid, selects payload. If an early
 // request is blocked, its identical payload moves into held on this edge.
 wire use_input=!old_request;
 // With early requests disabled, every valid request belongs to held.
 // Keep idle address on that same register, removing the unused EX-to-bus
 // path without changing accepted requests or adding a cycle.
 wire[31:0] request_address=EARLY_REQUEST && use_input ? launch_address : address;
 wire[31:0] request_data=use_input ? packet[116:85] : store_data;
 wire[2:0] request_f3=use_input ? packet[10:8] : f3;
 assign req_valid=!kill && (old_request || early_request);
 assign req_addr=request_address;
 assign req_data=req_write ? (store_data << {address[1:0],3'b0}) : 32'b0;
 assign req_mask=!req_write ? 4'b1111 : f3[1:0]==0 ? (4'b1<<address[1:0]) : f3[1:0]==1 ? (4'b11<<address[1:0]) : 4'b1111;
 assign req_write=!kill && old_request && kind==5;
 assign rsp_ready=posted_response || (memory_pending && sent && !kill);
 assign write_address=address;
 assign mul_tag=tag;assign mul_consume=wb_valid && multiply_access;
 assign wb_valid=!kill && complete;
 assign wb_side=secondary_multiply ? {held_side[64:32],mul_data} : held_side;
 wire[31:0] completed_result=memory_access ? loaded : primary_multiply ? mul_data : result;
 assign wb_packet={tag,pc,insn,next_pc,completed_result,address,store_data,
                  response_error ? address : tval,csr_data,
                  response_error ? (kind==5 ? 5'd7 : 5'd5) : cause,rd,f3,kind,wr,
                  exception || response_error,csr_we,serial};
 reg load_word,load_signed_byte,load_signed_half;
 reg[3:0] load_byte_lane;reg[1:0] load_half_lane;
 wire[7:0] picked_byte=({8{load_byte_lane[0]}} & rsp_data[7:0]) |
                       ({8{load_byte_lane[1]}} & rsp_data[15:8]) |
                       ({8{load_byte_lane[2]}} & rsp_data[23:16]) |
                       ({8{load_byte_lane[3]}} & rsp_data[31:24]);
 wire[15:0] picked_half=({16{load_half_lane[0]}} & rsp_data[15:0]) |
                        ({16{load_half_lane[1]}} & rsp_data[31:16]);
 wire[31:0] loaded=({32{load_word}} & rsp_data) |
                   {{24{load_signed_byte && picked_byte[7]}},picked_byte} |
                   {{16{load_signed_half && picked_half[15]}},picked_half};

 always @(posedge clk) begin
  if(!slot_valid || complete) begin held<=packet;held_side<=side_packet;held_l0_hit<=ENABLE_L0_CACHE && l0_hit;end
  if(!slot_valid || complete) begin
   load_word<=packet[10:8]==2;
   load_signed_byte<=packet[10:8]==0;load_signed_half<=packet[10:8]==1;
   load_byte_lane<=packet[9:8]==0 ? (4'b1<<input_address[1:0]) : 4'b0;
   load_half_lane<=packet[9:8]==1 ? (2'b1<<input_address[1]) : 2'b0;
  end
 end
 // A detached accepted write is architectural and must drain through a
 // younger trap/flush. No store address/data bypass or write buffer added.
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) posted_response<=0;
  else if(posted_fire) posted_response<=1;
  else if(posted_response && rsp_valid) posted_response<=0;
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin slot_valid<=0;sent<=0;end
  else if(kill) begin slot_valid<=0;sent<=0;end
  else begin
   if(start) begin slot_valid<=1;sent<=early_request && req_ready;end
   else begin
    if(complete) slot_valid<=0;
    if(old_request && req_ready) sent<=1;
   end
  end
 end
endmodule
