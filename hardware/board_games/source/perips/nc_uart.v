// Simple 8N1 TX peripheral. Payload and baud timing are independent of CPU.
module nc_uart #(parameter CLOCK_HZ=75000000,BAUD=115200)(
 input wire clk,rst_n,send,input wire[7:0] data,output wire ready,output wire tx);
 localparam DIV=(CLOCK_HZ+BAUD/2)/BAUD;
 reg[15:0] baud_count;reg[3:0] bits_left;reg[9:0] shift;
 assign ready=bits_left==0;assign tx=ready ? 1'b1 : shift[0];
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin baud_count<=0;bits_left<=0;shift<=10'h3ff;end
  else if(ready) begin
   if(send) begin shift<={1'b1,data,1'b0};bits_left<=10;baud_count<=DIV-1;end
  end else if(baud_count==0) begin
   baud_count<=DIV-1;shift<={1'b1,shift[9:1]};bits_left<=bits_left-1'b1;
  end else baud_count<=baud_count-1'b1;
 end
endmodule
