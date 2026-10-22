`timescale 1ns/1ps
// Exhaust all source matches in every legal circular allocation interval.
// Compare actual fixed-slot RTL with the previous head-ordered specification.
module dependency_priority_tb;
 reg clk=0,rst_n=0;
 nc_core dut(.clk(clk),.rst_n(rst_n),.irq_soft(1'b0),.irq_timer(1'b0),.irq_ext(1'b0),
  .i_req_valid(),.i_req_ready(1'b0),.i_addr(),.i_rsp_valid(1'b0),.i_rsp_ready(),.i_data(32'b0),.i_error(1'b0),
  .d_req_valid(),.d_req_ready(1'b0),.d_addr(),.d_wdata(),.d_mask(),.d_write(),
  .d_rsp_valid(1'b0),.d_rsp_ready(),.d_rdata(32'b0),.d_error(1'b0),
  .trace_valid(),.trace_trap(),.trace_pc(),.trace_insn(),.trace_data(),.trace_cause(),.trace_rd());
 integer h,len,mask,k,slot,n,checks=0;reg[7:0] live_set;
 reg expected_a,expected_b;reg[2:0] tag_a,tag_b;
 initial begin
  #1;force dut.id_insn=32'h002081b3; // ADD x3,x1,x2; both sources used.
  for(h=0;h<8;h=h+1) for(len=0;len<=8;len=len+1) for(mask=0;mask<(1<<len);mask=mask+1) begin
   live_set=0;
   for(k=0;k<8;k=k+1) dut.destination[k]=0;
   for(k=0;k<len;k=k+1) begin
    slot=(h+k)&7;live_set[slot]=1;dut.destination[slot]=((mask>>k)&1) ? 1 : 2;
   end
   dut.head=h[2:0];dut.tail=(h+len)&7;dut.live=live_set;
   expected_a=0;expected_b=0;tag_a=0;tag_b=0;
   for(n=0;n<8;n=n+1) begin
    slot=(h+n)&7;
    if(live_set[slot]) begin
     if(dut.destination[slot]==1) begin expected_a=1;tag_a=slot[2:0];end
     if(dut.destination[slot]==2) begin expected_b=1;tag_b=slot[2:0];end
    end
   end
   #2;
   if(dut.dep_a!==expected_a || dut.dep_b!==expected_b || dut.tag_a!==tag_a || dut.tag_b!==tag_b)
    $fatal(1,"dependency priority h=%0d len=%0d matches=%h",h,len,mask);
   checks=checks+1;
  end
  $display("PASS dependency priority checks=%0d (all heads, lengths, match masks)",checks);$finish;
 end
endmodule
