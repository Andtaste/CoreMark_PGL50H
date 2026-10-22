`timescale 1ns/1ps
// Clock/reset shim only: PLL frequency itself is independently verified by routed STA.
module pll(input clkin1,output clkout0,pll_lock);assign clkout0=clkin1;assign pll_lock=1'b1;endmodule
module uart80_tb;
 reg clk=0,rst=0;always #6.25 clk=~clk;wire tx;wire[1:0] gpio;
 top dut(.clk(clk),.rst_ext_i(rst),.uart_rx_pin(1'b1),.uart_tx_pin(tx),.halted_ind(),.gpio(gpio),.jtag_TCK(1'b0),.jtag_TMS(1'b0),.jtag_TDI(1'b0),.jtag_TDO());
 integer bit_no,k;reg[9:0] frame=10'b1101001010;
 initial begin
 repeat(4) @(negedge clk);rst=1;repeat(8) @(negedge clk);
 if(dut.soc.bus.CLOCK_HZ!=80000000 || dut.soc.bus.uart.DIV!=694) $fatal(1,"Physical top/UART frequency configuration mismatch");
 force dut.soc.bus.uart_send=1'b1;force dut.soc.bus.dw=32'ha5;
 @(negedge clk);release dut.soc.bus.uart_send;release dut.soc.bus.dw;
 for(bit_no=0;bit_no<10;bit_no=bit_no+1) begin
  for(k=0;k<694;k=k+1) begin
   if(tx!==frame[bit_no]) $fatal(1,"UART80 frame mismatch bit=%0d cycle=%0d",bit_no,k);
   @(negedge clk);
  end
 end
 if(tx!==1 || !dut.soc.bus.uart.ready) $fatal(1,"UART80 did not finish frame");
 $display("PASS physical top CLOCK_HZ=80000000 DIV=694; A5 8N1 exact 694-cycle bits");$finish;
 end
 initial begin #200000;$fatal(1,"timeout");end
 endmodule
