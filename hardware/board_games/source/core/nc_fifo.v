// Original new_core RTL. Non-fall-through two-entry timing boundary.
// in_ready depends ONLY on registered occupancy, never on out_ready.
module nc_fifo #(parameter WIDTH=32,parameter DEPTH=2)(
 input wire clk,rst_n,clear,
 input wire in_valid, output wire in_ready, input wire [WIDTH-1:0] in_data,
 output wire out_valid,input wire out_ready,output wire [WIDTH-1:0] out_data
);
 localparam PTR=$clog2(DEPTH),CNT=$clog2(DEPTH+1);
 reg [WIDTH-1:0] data[0:DEPTH-1];
 reg[PTR-1:0] rd,wr; reg[CNT-1:0] count;
 assign in_ready=count!=DEPTH;
 assign out_valid=count!=0;
 assign out_data=data[rd];
 wire push=in_valid && in_ready;
 wire pop=out_valid && out_ready;
 always @(posedge clk) if(push) data[wr]<=in_data;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin rd<=0;wr<=0;count<=0;end
  else if(clear) begin rd<=0;wr<=0;count<=0;end
  else begin
   if(push) wr<=wr+1'b1;
   if(pop) rd<=rd+1'b1;
   case({push,pop}) 2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:;endcase
  end
 end
endmodule
