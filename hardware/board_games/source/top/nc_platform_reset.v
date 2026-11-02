// Start the menu without DDR. A later calibration loss aborts CPU transactions
// by returning the CPU to reset,then releases it back to the DDR-independent menu.
module nc_platform_reset(input wire clk,base_reset_n,ddr_ready,output wire cpu_rst_n);
 reg previous_ready;reg[3:0] release_pipe;
 always @(posedge clk or negedge base_reset_n)begin
  if(!base_reset_n)begin previous_ready<=0;release_pipe<=0;end
  else begin
   previous_ready<=ddr_ready;
   if(previous_ready && !ddr_ready)release_pipe<=0;
   else release_pipe<={release_pipe[2:0],1'b1};
  end
 end
 assign cpu_rst_n=release_pipe[3];
endmodule
