`timescale 1ns/1ps
module fetch_equivalence_tb;
 reg clk=0;always #5 clk=!clk;
 reg rst_n=0,redirect=0,stop=0,ready=0,req_ready=0,rsp_valid=0,rsp_error=0;
 reg[31:0] target=0,rsp_data=0;
 wire[1:0] req_valid,rsp_ready,valid,fault;
 wire[31:0] req_addr[0:1],pc[0:1],inst[0:1];
 old_nc_fetch reference(.clk(clk),.rst_n(rst_n),.redirect(redirect),.stop(stop),.target(target),
  .req_valid(req_valid[0]),.req_ready(req_ready),.req_addr(req_addr[0]),
  .rsp_valid(rsp_valid),.rsp_ready(rsp_ready[0]),.rsp_data(rsp_data),.rsp_error(rsp_error),
  .valid(valid[0]),.ready(ready),.pc(pc[0]),.inst(inst[0]),.fault(fault[0]));
 nc_fetch #(.ENABLE_BP(0)) dut(.clk(clk),.rst_n(rst_n),.redirect(redirect),.stop(stop),.target(target),
  .bp_flush(1'b0),.bp_update_valid(1'b0),.bp_update_branch(1'b0),.bp_update_conditional(1'b0),
  .bp_update_taken(1'b0),.bp_update_pc(32'b0),.bp_update_target(32'b0),.prediction(),
  .req_valid(req_valid[1]),.req_ready(req_ready),.req_addr(req_addr[1]),
  .rsp_valid(rsp_valid),.rsp_ready(rsp_ready[1]),.rsp_data(rsp_data),.rsp_error(rsp_error),
  .valid(valid[1]),.ready(ready),.pc(pc[1]),.inst(inst[1]),.fault(fault[1]));
 reg pending=0;integer delay_left=0;
 reg[31:0] address=0,rng=32'h92b74135;
 integer cycle=0,seed=0,empty_insert=0,single_turnover=0,refill=0,wraps=0;
 integer stalled_redirect=0,stale_response=0,full_seen=0,full_redirect=0;
 function[31:0] next_random(input[31:0] x);
  next_random=x*32'd1664525+32'd1013904223;
 endfunction
 initial begin
  if($value$plusargs("seed=%d",seed)) rng=seed;
 end
 always @(negedge clk) begin
  rst_n=cycle>=3;
  rng=next_random(rng);ready=rng[31:28]<11;req_ready=rng[27:24]<12;
  stop=rng[23:20]==0;redirect=rng[19:14]==0;target={rng[29:0],2'b0};
  // Long consume stalls fill the queue; following full-speed windows drain it.
  if(cycle%800<100) begin ready=0;stop=0;redirect=0;req_ready=1;end
  if(cycle%800>=100 && cycle%800<160) begin ready=1;stop=0;redirect=0;req_ready=1;end
  // Flush a full queue, and flush a published bus-stalled command.
  if(cycle%800==80) redirect=1;
  if(cycle%800==300) begin req_ready=0;redirect=1;end
  rsp_valid=pending && delay_left==0;
  rsp_data=address ^ 32'h6d829ca1;rsp_error=address[9:5]==5'b10101;
 end
 always @(posedge clk) begin
  cycle<=cycle+1;
  if(!rst_n) begin pending<=0;delay_left<=0;end
  else begin
   if(req_valid[0]!==req_valid[1] || rsp_ready[0]!==rsp_ready[1] || valid[0]!==valid[1])
    $fatal(1,"handshake mismatch cycle=%0d",cycle);
   if(req_valid[0] && req_addr[0]!==req_addr[1]) $fatal(1,"request mismatch cycle=%0d",cycle);
   if(valid[0] && {pc[0],inst[0],fault[0]}!=={pc[1],inst[1],fault[1]})
    $fatal(1,"head mismatch cycle=%0d pc=%h/%h inst=%h/%h",cycle,pc[0],pc[1],inst[0],inst[1]);
   if(pending && delay_left>0) delay_left<=delay_left-1;
   if(rsp_valid && rsp_ready[0]) pending<=0;
   if(req_valid[0] && req_ready) begin
    if(pending && !(rsp_valid && rsp_ready[0])) $fatal(1,"multiple outstanding requests");
    pending<=1;address<=req_addr[0];
    delay_left<=cycle%800<160 ? 0 : {29'b0,rng[12:10]};
   end
   if(reference.push && reference.count==0) empty_insert<=empty_insert+1;
   if(reference.push && reference.pop && reference.count==1) single_turnover<=single_turnover+1;
   if(reference.pop && reference.count>1) refill<=refill+1;
   if(reference.pop && reference.rd==7) wraps<=wraps+1;
   if(reference.count==8) full_seen<=full_seen+1;
   if(redirect && reference.count==8) full_redirect<=full_redirect+1;
   if(redirect && req_valid[0] && !req_ready) stalled_redirect<=stalled_redirect+1;
   if(rsp_valid && reference.flight_stale) stale_response<=stale_response+1;
   if(cycle==100003) begin
    if(empty_insert==0 || single_turnover==0 || refill==0 || wraps==0 || full_seen==0 ||
       full_redirect==0 || stalled_redirect==0 || stale_response==0) $fatal(1,"coverage missing");
    $display("PASS fetch equivalence cycles=100000 empty=%0d turnover=%0d refill=%0d wrap=%0d full=%0d full_redirect=%0d stalled_redirect=%0d stale=%0d",
     empty_insert,single_turnover,refill,wraps,full_seen,full_redirect,stalled_redirect,stale_response);
    $finish;
   end
  end
 end
endmodule
