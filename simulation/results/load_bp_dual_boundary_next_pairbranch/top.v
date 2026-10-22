// Same board pin names; CPU debug/JTAG is intentionally not implemented.
module top(input wire clk,rst_ext_i,input wire uart_rx_pin,
 output wire uart_tx_pin,halted_ind,inout wire[1:0] gpio,
 input wire jtag_TCK,jtag_TMS,jtag_TDI,output wire jtag_TDO);
 wire sys_clk,locked;reg[3:0] reset_sync;
 wire arst_n=rst_ext_i && locked;
 always @(posedge sys_clk or negedge arst_n) begin
  if(!arst_n) reset_sync<=0;else reset_sync<={reset_sync[2:0],1'b1};
 end
 pll clock_ip(.clkin1(clk),.clkout0(sys_clk),.pll_lock(locked));
 wire[31:0] tohost;wire[1:0] gpio_out;
 nc_soc #(.CLOCK_HZ(80000000)) soc(.clk(sys_clk),.rst_n(reset_sync[3]),.irq_soft(1'b0),.irq_ext(1'b0),
  .uart_tx(uart_tx_pin),.gpio_out(gpio_out),.tohost(tohost));
 assign gpio=gpio_out;assign halted_ind=tohost==1;assign jtag_TDO=1'b0;
endmodule
