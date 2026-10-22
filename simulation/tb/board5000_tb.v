`timescale 1ns/1ps
// Full instruction execution, synchronous dual-port RAM, independently decoded UART.
// Only UART is accelerated; benchmark CPU/RAM timing and all RTL remain unchanged.
module board5000_tb;
 reg clk=0;always #6.097561 clk=~clk;reg rst_n=0;
 wire tx;wire[1:0] gpio;wire[31:0] tohost;
 nc_soc #(.CLOCK_HZ(82000000)) dut(.clk(clk),.rst_n(rst_n),.irq_soft(1'b0),.irq_ext(1'b0),.uart_tx(tx),.gpio_out(gpio),.tohost(tohost));
 integer uart_fd,bit_index;reg[7:0] uart_byte;reg[4095:0] uartfile;
 longint unsigned ticks=0,ref_cycles=0,ref_retired=0,ref_secondary=0,ref_loads=0,ref_stores=0,ref_bjp=0;
 integer finish_count=0;reg check_stats=0;longint unsigned limit=2000000000;
 initial begin
  if(!$value$plusargs("uart=%s",uartfile)) $fatal(1,"UART output path required");
  if($value$plusargs("limit=%d",limit)) begin end
  uart_fd=$fopen(uartfile,"wb");if(!uart_fd) $fatal(1,"Cannot open UART output");
  repeat(5) @(negedge clk);rst_n=1;
 end
 initial forever begin
  @(negedge tx);
  if(rst_n) begin
   repeat(4) @(posedge clk);if(tx!==0) $fatal(1,"UART start error");
   for(bit_index=0;bit_index<8;bit_index=bit_index+1) begin repeat(8) @(posedge clk);uart_byte[bit_index]=tx;end
   repeat(8) @(posedge clk);if(tx!==1) $fatal(1,"UART stop error");
   $fwrite(uart_fd,"%c",uart_byte);$fflush(uart_fd);
  end
 end
 always @(posedge clk) if(rst_n) begin
  ticks=ticks+1;
  if(ticks%100000000==0) begin $display("PROGRESS cycles=%0d PC=%08x",ticks,dut.cpu.w_pc);$fflush();end
  if(ticks>limit) $fatal(1,"SOC timeout PC=%h",dut.cpu.w_pc);
  if(dut.cpu.wb_valid && (!dut.cpu.live[dut.cpu.w_tag] || dut.cpu.w_tag!=dut.cpu.head)) $fatal(1,"Retirement order mismatch");
  if(dut.cpu.commit1 && (!dut.cpu.commit || dut.cpu.w1_pc!=dut.cpu.w_pc+4)) $fatal(1,"Invalid secondary retirement");
  if(dut.cpu.trace_trap && dut.cpu.trace_valid) $fatal(1,"Unexpected benchmark exception PC=%h cause=%h",dut.cpu.trace_pc,dut.cpu.trace_cause);
  check_stats=0;
  if(dut.cpu.csr.stats.control) begin
   if(dut.cpu.csr.stats.control_data[1]) begin ref_cycles=0;ref_retired=0;ref_secondary=0;ref_loads=0;ref_stores=0;ref_bjp=0;end
   else if(!dut.cpu.csr.stats.control_data[0]) check_stats=1;
  end else if(dut.cpu.csr.stats.enabled) begin
   ref_cycles=ref_cycles+1;
   if(dut.cpu.commit) begin
    ref_retired=ref_retired+(dut.cpu.commit1 ? 2 : 1);
    if(dut.cpu.commit1) begin ref_secondary=ref_secondary+1;if(dut.cpu.w1_insn[6:0]==7'h63) ref_bjp=ref_bjp+1;end
    case(dut.cpu.w_insn[6:0])
     7'h03:ref_loads=ref_loads+1;
     7'h23:ref_stores=ref_stores+1;
     7'h63,7'h6f,7'h67:ref_bjp=ref_bjp+1;
    endcase
   end
  end
  if(tohost!=0 && finish_count==0) begin if(tohost!=1) $fatal(1,"Software reported failure %h",tohost);finish_count=20;end
  if(finish_count!=0) begin
   finish_count=finish_count-1;
   if(finish_count==1) begin $display("PASS board firmware cycles=%0d",ticks);$fclose(uart_fd);$finish;end
  end
 end
 always @(negedge clk) if(check_stats) begin
  if(dut.cpu.csr.stats.counters[1]!=ref_cycles || dut.cpu.csr.stats.counters[9]!=ref_retired ||
     dut.cpu.csr.stats.counters[10]!=ref_secondary || dut.cpu.csr.stats.counters[11]!=ref_loads ||
     dut.cpu.csr.stats.counters[12]!=ref_stores || dut.cpu.csr.stats.counters[7]!=ref_bjp)
   $fatal(1,"Independent statistics mismatch");
  if(dut.cpu.csr.stats.overflow!=0) $fatal(1,"Statistics overflow");
  $display("COUNTER_CHECK_PASS cycles=%0d retired=%0d secondary=%0d loads=%0d stores=%0d bjp=%0d",ref_cycles,ref_retired,ref_secondary,ref_loads,ref_stores,ref_bjp);
 end
endmodule
