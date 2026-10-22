`timescale 1ns/1ps
module pll(input clkin1,output clkout0,pll_lock);assign clkout0=clkin1;assign pll_lock=1'b1;endmodule
module uart82_tb;
 reg clk=0,rst=0;always #6.097561 clk=~clk;wire tx;wire[1:0] gpio;
 top dut(.clk(clk),.rst_ext_i(rst),.uart_rx_pin(1'b1),.uart_tx_pin(tx),.halted_ind(),.gpio(gpio),.jtag_TCK(1'b0),.jtag_TMS(1'b0),.jtag_TDI(1'b0),.jtag_TDO());
 integer i,k;reg[9:0] frame=10'b1101001010;
 initial begin
 repeat(4) @(negedge clk);rst=1;repeat(8) @(negedge clk);
 if(dut.soc.bus.CLOCK_HZ!=82000000 || dut.soc.bus.uart.DIV!=712) $fatal(1,"CLOCK_HZ82/UART712 mismatch");
 force dut.soc.bus.uart_send=1'b1;force dut.soc.bus.dw=32'ha5;
 @(negedge clk);release dut.soc.bus.uart_send;release dut.soc.bus.dw;
 for(i=0;i<10;i=i+1) for(k=0;k<712;k=k+1) begin
 if(tx!==frame[i]) $fatal(1,"UART82 frame mismatch bit=%0d cycle=%0d",i,k);@(negedge clk);
 end
 if(tx!==1 || !dut.soc.bus.uart.ready) $fatal(1,"UART82 frame incomplete");
 $display("PASS actual top CLOCK_HZ82000000 DIV712 A5 exact-cycle 8N1");$finish;end
 initial begin #200000;$fatal(1,"timeout");end
endmodule
