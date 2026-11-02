// 8N1 receiver, center sampling, 2-FF input synchronizer, bounded byte FIFO.
// Full FIFO drops the arriving byte and sets sticky overflow; existing data survives.
module nc_uart_rx #(parameter CLOCK_HZ=70000000,BAUD=115200,ADDR_BITS=6)(
 input wire clk,rst_n,rx,pop,clear_overflow,clear_framing,
 output wire [7:0] data,output wire available,
 output reg [ADDR_BITS:0] count,output reg overflow,framing_error
);
 localparam DIV=(CLOCK_HZ+BAUD/2)/BAUD,DEPTH=1<<ADDR_BITS;
 localparam IDLE=0,START=1,BITS=2,STOP=3,WAIT_HIGH=4;
 (* async_reg="true" *) reg rx_meta,rx_sync;
 reg [2:0] state,bit_index;reg [15:0] timer;reg [7:0] shift;
 reg [7:0] fifo[0:DEPTH-1];reg [ADDR_BITS-1:0] rd_ptr,wr_ptr;
 wire stop_sample=state==STOP && timer==0;
 wire arrived=stop_sample && rx_sync;
 wire take=pop && available;
 wire put=arrived && (count<DEPTH || take);
 assign available=count!=0;
 assign data=available ? fifo[rd_ptr] : 8'd0;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin rx_meta<=1;rx_sync<=1;end
  else begin rx_meta<=rx;rx_sync<=rx_meta;end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=IDLE;timer<=0;bit_index<=0;shift<=0;end
  else case(state)
   IDLE:if(!rx_sync)begin state<=START;timer<=DIV/2-1;end
   START:if(timer!=0)timer<=timer-1'b1;
         else if(rx_sync)state<=IDLE;
         else begin state<=BITS;timer<=DIV-1;bit_index<=0;end
   BITS:if(timer!=0)timer<=timer-1'b1;
        else begin
         shift[bit_index]<=rx_sync;timer<=DIV-1;
         if(bit_index==7)state<=STOP;else bit_index<=bit_index+1'b1;
        end
   STOP:if(timer!=0)timer<=timer-1'b1;
        else state<=rx_sync?IDLE:WAIT_HIGH;
   WAIT_HIGH:if(rx_sync)state<=IDLE; // Break must not manufacture zero bytes.
   default:state<=IDLE;
  endcase
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin rd_ptr<=0;wr_ptr<=0;count<=0;overflow<=0;framing_error<=0;end
  else begin
   if(clear_overflow)overflow<=0;
   if(clear_framing)framing_error<=0;
   if(arrived && !put)overflow<=1;
   if(stop_sample && !rx_sync)framing_error<=1;
   if(put)begin fifo[wr_ptr]<=shift;wr_ptr<=wr_ptr+1'b1;end
   if(take)rd_ptr<=rd_ptr+1'b1;
   case({put,take})
    2'b10:count<=count+1'b1;
    2'b01:count<=count-1'b1;
    default:;
   endcase
  end
 end
endmodule
