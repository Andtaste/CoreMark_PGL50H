`timescale 1ns/1ps
module stats_tb;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,control=0;reg[31:0] control_data=0;reg[13:0] events=0;
 reg[3:0] addr=0;wire[31:0] data;
 nc_stats dut(.*);
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 initial begin
  tick;rst_n=1;control=1;control_data=3;events=14'h3fff;tick;
  control=0;repeat(5) tick;
  control=1;control_data=0;tick; // Includes last sampled cycle, excludes stop.
  addr=1;#1;if(data!=5) $fatal(1,"window cycle count %d",data);
  addr=9;#1;if(data!=5) $fatal(1,"same-window retire count %d",data);
  control=0;repeat(3) tick;
  addr=1;#1;if(data!=5) $fatal(1,"freeze failed");
  control=1;control_data=3;tick;control=0;
  // Exercise rollover without simulating 2^32 cycles.
  dut.counters[1]=32'hffffffff;events=1;tick;tick;
  control=1;control_data=0;tick;
  addr=8;#1;if(data[0]!=1) $fatal(1,"sticky overflow missing");
  control_data=2;tick;
  addr=8;#1;if(data!=0) $fatal(1,"clear overflow failed");
  addr=1;#1;if(data!=0) $fatal(1,"clear count failed");
  addr=10;#1;if(data!=0) $fatal(1,"single-issue secondary count");
  addr=15;#1;if(data!=32'h4e430004) $fatal(1,"ABI signature");
  $display("PASS stats clear/enable/freeze/drain/overflow/signature");$finish;
 end
endmodule
