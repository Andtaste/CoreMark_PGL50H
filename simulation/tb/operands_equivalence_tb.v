`timescale 1ns/1ps
module operands_equivalence_tb;
 reg clk=0;always #5 clk=~clk;reg rst_n=0,clear=0;
 reg in_valid=0,out_ready=0;reg[203:0] in_packet=0;reg[2:0] in_tag=0,tag_a=0,tag_b=0;
 reg[18:0] in_control=0;reg[31:0] in_prediction=0;
 reg wait_a=0,wait_b=0,f_valid=0,m_valid=0,w_valid=0;
 reg[2:0] f_tag=0,m_tag=0,w_tag=0;reg[31:0] f_data=0,m_data=0,w_data=0;
 wire ready0,ready1,valid0,valid1,occupied0,occupied1;
 wire[203:0] packet0,packet1;wire[18:0] control0,control1;wire[31:0] prediction0,prediction1;wire[2:0] token0,token1;
 nc_operands dut(.clk(clk),.rst_n(rst_n),.clear(clear),.in_valid(in_valid),.in_ready(ready0),
  .in_packet(in_packet),.in_tag(in_tag),.in_control(in_control),.out_control(control0),
  .in_prediction(in_prediction),.out_prediction(prediction0),.wait_a(wait_a),.wait_b(wait_b),.tag_a(tag_a),.tag_b(tag_b),
  .f_valid(f_valid),.f_tag(f_tag),.f_data(f_data),.m_valid(m_valid),.m_tag(m_tag),.m_data(m_data),
  .w_valid(w_valid),.w_tag(w_tag),.w_data(w_data),.out_valid(valid0),.out_ready(out_ready),
  .out_packet(packet0),.out_tag(token0),.occupied(occupied0));
 old_nc_operands ref_dut(.clk(clk),.rst_n(rst_n),.clear(clear),.in_valid(in_valid),.in_ready(ready1),
  .in_packet(in_packet),.in_tag(in_tag),.in_control(in_control),.out_control(control1),
  .in_prediction(in_prediction),.out_prediction(prediction1),.wait_a(wait_a),.wait_b(wait_b),.tag_a(tag_a),.tag_b(tag_b),
  .f_valid(f_valid),.f_tag(f_tag),.f_data(f_data),.m_valid(m_valid),.m_tag(m_tag),.m_data(m_data),
  .w_valid(w_valid),.w_tag(w_tag),.w_data(w_data),.out_valid(valid1),.out_ready(out_ready),
  .out_packet(packet1),.out_tag(token1),.occupied(occupied1));
 integer i,k,seed=17,pushes=0,pops=0,full=0,insert_forward=0,duplicates=0,clears=0;
 reg[31:0] rng;
 function[31:0] step(input[31:0] v);reg[31:0] x;begin x=v^(v<<13);x=x^(x>>17);step=x^(x<<5);end endfunction
 task compare;
  begin
   if({ready0,valid0,occupied0}!={ready1,valid1,occupied1}) $fatal(1,"operand handshake differs cycle=%0d",i);
   if(valid0 && {packet0,control0,prediction0,token0}!=={packet1,control1,prediction1,token1})
    $fatal(1,"operand value/metadata differs cycle=%0d new=%h old=%h",i,packet0,packet1);
  end
 endtask
 initial begin
  if($value$plusargs("seed=%d",seed)) begin end
  rng=seed;repeat(3) @(negedge clk);rst_n=1;
  for(i=0;i<100000;i=i+1) begin
   @(negedge clk);rng=step(rng);
   clear=i%173==172;in_valid=rng[0] || rng[1];out_ready=rng[2] || rng[3];
   in_tag=rng[6:4];tag_a=rng[9:7];tag_b=rng[12:10];wait_a=rng[13];wait_b=rng[14];
   f_valid=rng[15];m_valid=rng[16];w_valid=rng[17];f_tag=rng[20:18];m_tag=rng[23:21];w_tag=rng[26:24];
   // Deliberate same-tag, unequal-data broadcasts verify the old F>M>W
   // priority; they are stronger than the core's equal-duplicate invariant.
   if(i%11==0) begin f_valid=1;m_valid=1;w_valid=1;f_tag=tag_a;m_tag=tag_a;w_tag=tag_a;end
   for(k=0;k<7;k=k+1) begin rng=step(rng);in_packet=(in_packet<<32)|rng;end
   rng=step(rng);f_data=rng;rng=step(rng);m_data=rng;rng=step(rng);w_data=rng;
   rng=step(rng);in_prediction=rng;rng=step(rng);in_control=rng[18:0];
   #1;compare;
   if(in_valid && ready0) begin
    pushes=pushes+1;
    if(wait_a && ((f_valid && f_tag==tag_a)||(m_valid && m_tag==tag_a)||(w_valid && w_tag==tag_a))) insert_forward=insert_forward+1;
   end
   if(valid0 && out_ready) pops=pops+1;if(!ready0) full=full+1;
   if(i%11==0) duplicates=duplicates+1;if(clear) clears=clears+1;
   @(posedge clk);#1;compare;
  end
  if(pushes<10000 || pops<10000 || full<10000 || insert_forward<1000 || clears<500) $fatal(1,"missing operand coverage");
  $display("PASS operands equivalence cycles=100000 seed=%0d pushes=%0d pops=%0d full=%0d insertion_forward=%0d duplicate_priority=%0d clears=%0d",seed,pushes,pops,full,insert_forward,duplicates,clears);$finish;
 end
endmodule
