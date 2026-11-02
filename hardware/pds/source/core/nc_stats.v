// Observation only: events are registered before incrementing counters.
// CSR 7c0: bit0 enable, bit1 clear. 7c8: sticky overflow (bit = CSR offset-1).
// A stop drains the previous sample; a clear discards it. Control-write cycles
// are excluded. The same qualification applies to cycles and retirements.
module nc_stats(input wire clk,rst_n,
 input wire control,input wire[31:0] control_data,
 input wire[13:0] events,input wire[3:0] addr,output reg[31:0] data);
 reg enabled;reg[13:0] sample,overflow;reg[31:0] counters[1:14];
 integer i;
 always @* begin
  case(addr)
   0:data={31'b0,enabled};
   8:data={18'b0,overflow};
   15:data=32'h4e430004; // NC statistics ABI 4; deliberately distinct from old CPU.
   default:data=counters[addr];
  endcase
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   enabled<=0;sample<=0;overflow<=0;
   for(i=1;i<=14;i=i+1) counters[i]<=0;
  end else begin
   sample<=(enabled && !control) ? events : 14'b0;
   if(control) enabled<=control_data[0];
   if(control && control_data[1]) begin
    sample<=0;overflow<=0;
    for(i=1;i<=14;i=i+1) counters[i]<=0;
   end else begin
    for(i=1;i<=14;i=i+1) if(i!=8 && sample[i-1]) begin
     counters[i]<=counters[i]+((i==9 && sample[9]) ? 32'd2 : 32'd1);
     if((&counters[i]) || (i==9 && sample[9] && counters[i]==32'hfffffffe)) overflow[i-1]<=1;
    end
   end
  end
 end
endmodule
