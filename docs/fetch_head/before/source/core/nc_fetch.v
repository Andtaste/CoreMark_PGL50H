// IF: one published command, one in-flight response, eight queued words.
// Response/next-request turnover supports one word/cycle. Credit uses only
// registered occupancy. Stalled commands survive redirects and are drained.
module nc_fetch(input wire clk,rst_n,redirect,stop,input wire[31:0] target,
 output wire req_valid,input wire req_ready,output wire[31:0] req_addr,
 input wire rsp_valid,output wire rsp_ready,input wire[31:0] rsp_data,input wire rsp_error,
 output wire valid,input wire ready,output wire[31:0] pc,inst,output wire fault);
 reg[31:0] next_pc,cmd_pc,flight_pc;
 reg cmd_valid,cmd_stale,flight,flight_stale;
 // PC/fault have a direct FF source. Keep their FIFO in FFs to avoid the
 // 0-logic-level FF -> LUT RAM write-data hold path on PGL50H. Instruction
 // data still uses distributed RAM; this mapping changes no cycle timing.
 reg[31:0] instructions[0:7] /* synthesis syn_ramstyle="lut_ram" */;
 reg[32:0] metadata[0:7] /* synthesis syn_ramstyle="registers" */;
 reg[2:0] rd,wr;reg[3:0] count;
 wire response=flight && rsp_valid;
 assign req_valid=cmd_valid && (!flight || response);
 assign req_addr=cmd_pc;assign rsp_ready=flight;
 wire launch=req_valid && req_ready;
 wire[4:0] reserved={1'b0,count}+{4'b0,flight}+{4'b0,cmd_valid};
 wire prepare=(!cmd_valid || launch) && reserved<8 && !stop && !redirect;
 wire push=response && !flight_stale && !redirect;
 wire pop=valid && ready;
 assign valid=count!=0;assign {fault,pc}=metadata[rd];assign inst=instructions[rd];
 always @(posedge clk) if(push) begin
  metadata[wr]<={rsp_error,flight_pc};instructions[wr]<=rsp_data;
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   next_pc<=0;cmd_pc<=0;flight_pc<=0;cmd_valid<=0;cmd_stale<=0;flight<=0;flight_stale<=0;
   rd<=0;wr<=0;count<=0;
  end else begin
   if(launch) begin cmd_valid<=0;flight<=1;flight_pc<=cmd_pc;flight_stale<=cmd_stale || redirect;end
   else if(response) flight<=0;
   if(prepare) begin cmd_valid<=1;cmd_pc<=next_pc;cmd_stale<=0;next_pc<=next_pc+4;end
   if(push) wr<=wr+1'b1;if(pop) rd<=rd+1'b1;
   case({push,pop}) 2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:;endcase
   if(redirect) begin
    rd<=0;wr<=0;count<=0;next_pc<=target;
    // redirect/target already crossed a register in the core. Capture the
    // target request now, instead of waiting a second cycle to prepare it.
    // Preserve any published request that is stalled by the bus.
    if(cmd_valid && !launch) cmd_stale<=1;
    else begin cmd_valid<=1;cmd_pc<=target;cmd_stale<=0;next_pc<=target+32'd4;end
    if(flight && !launch) flight_stale<=1;
   end
  end
 end
endmodule
