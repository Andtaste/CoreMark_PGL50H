`timescale 1ns/1ps
// Accepted-packet scoreboard, independently timed bus, and a registered WB
// fault-to-kill boundary. No DUT internal state is used by the reference.
module memory_overlap_tb;
 reg clk=0;always #5 clk=~clk;reg rst_n=0,kill=0,valid=0;
 reg[279:0] packet=0;reg req_ready=0,rsp_valid=0,rsp_error=0;
 reg[31:0] rsp_data=0;reg mul_ready=0;wire[31:0] mul_data=32'hdeaf0000^{29'b0,mul_tag};
 wire ready,wb_valid,req_valid,req_write,rsp_ready,mul_consume;
 wire[279:0] wb_packet;wire[31:0] req_addr,req_data;wire[3:0] req_mask;wire[2:0] mul_tag;
 nc_memory dut(.clk(clk),.rst_n(rst_n),.kill(kill),.valid(valid),.ready(ready),.packet(packet),
  .wb_valid(wb_valid),.wb_packet(wb_packet),.mul_tag(mul_tag),.mul_ready(mul_ready),.mul_data(mul_data),.mul_consume(mul_consume),
  .req_valid(req_valid),.req_ready(req_ready),.req_addr(req_addr),.req_data(req_data),.req_mask(req_mask),.req_write(req_write),
  .rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_data(rsp_data),.rsp_error(rsp_error));
 reg[279:0] expected[0:16383];integer ew=0,er=0;
 reg bus_pending=0,bus_error=0;reg[31:0] bus_raw;integer bus_delay=0;
 reg[31:0] rng=32'h249187ac;integer cycle,seq=0,accepts=0,completions=0,requests=0,faults=0;
 integer buffered_turns=0,overlap_requests=0,muls=0,stalls=0;
 reg last_accept=0,stalled=0;reg[68:0] stable_request;
 reg[279:0] e;reg accept_now,response_now,request_now;reg[3:0] kind;
 function[31:0] advance(input[31:0] x);advance=x*32'd1664525+32'd1013904223;endfunction
 function[279:0] instruction(input integer id);
  reg[3:0] k;reg fault;
  begin
   case(id%7) 0,3:k=4;1,4:k=0;2:k=5;5:k=6;default:k=7;endcase
   fault=k==0 && id%37==1;
   instruction={id[2:0],32'h1000+id*32'd4,32'h93,32'h1004+id*32'd4,32'ha5000000^id,
    32'h10000000+id*32'd4,32'hbeef0000^id,32'h12345678,32'h11223344,
    (fault ? 5'd2 : 5'd0),5'd10,3'd2,k,(k!=5),fault,(k==7),1'b0};
  end
 endfunction
 always @(posedge clk) if(rst_n) begin
  accept_now=valid && ready;request_now=req_valid && req_ready;response_now=rsp_valid && rsp_ready;
  if(stalled && !kill && (!req_valid || {req_write,req_mask,req_data,req_addr}!==stable_request))
   $fatal(1,"request changed while stalled");
  stalled=req_valid && !req_ready;stable_request={req_write,req_mask,req_data,req_addr};
  if(kill) begin
   if(req_valid || wb_valid || ready || mul_consume) $fatal(1,"kill did not suppress MEM effects");
   if(ew!=er || bus_pending) $fatal(1,"younger accepted instruction survived precise fault");
  end
  if(accept_now) begin
   e=packet;kind=packet[7:4];
   if(!packet[2] && (kind==4 || kind==5)) begin
    if(!request_now || req_addr!==packet[148:117] || req_data!==packet[116:85] || req_mask!==4'hf || req_write!==(kind==5))
     $fatal(1,"request/accepted packet mismatch");
   end else if(kind==6 && !packet[2]) begin
    if(!mul_ready || !mul_consume) $fatal(1,"multiply completion not consumed exactly once");
    e[180:149]=mul_data;muls=muls+1;
   end
   expected[ew]=e;ew=ew+1;accepts=accepts+1;
  end
  if(mul_consume && !(accept_now && packet[7:4]==6 && !packet[2])) $fatal(1,"unexpected multiply consume");
  if(wb_valid) begin
   if(er==ew) $fatal(1,"unowned WB");e=expected[er];
   if(!e[2] && (e[7:4]==4 || e[7:4]==5)) begin
    if(!response_now || !bus_pending) $fatal(1,"memory completion without response");
    e[180:149]=bus_raw;
    if(bus_error) begin e[84:53]=e[148:117];e[20:16]=e[7:4]==5 ? 7 : 5;e[2]=1;end
   end
   if(wb_packet!==e) $fatal(1,"WB order/value mismatch er=%0d expected=%h actual=%h",er,e,wb_packet);
   if(e[2]) begin
    faults=faults+1;
    if(request_now || (accept_now && expected[ew-1][279:245]!=e[279:245])) $fatal(1,"fault authorized younger instruction");
   end
   if(accept_now && packet[7:4]==4 && e[7:4]!=4 && e[7:4]!=5) overlap_requests=overlap_requests+1;
   if(response_now && accept_now && packet[7:4]!=4 && packet[7:4]!=5) buffered_turns=buffered_turns+1;
   er=er+1;completions=completions+1;
  end
  kill<=wb_valid && wb_packet[2];
  if(response_now) bus_pending=0;
  if(request_now) begin
   if(bus_pending) $fatal(1,"more than one bus transaction");
   requests=requests+1;bus_pending=1;bus_delay=(requests%4);bus_raw=32'hf00d8001^req_addr;bus_error=requests%19==7;
  end else if(bus_delay>0) bus_delay=bus_delay-1;
  if(req_valid && !req_ready) stalls=stalls+1;
  last_accept=accept_now;
 end
 initial begin
  repeat(3) @(negedge clk);rst_n=1;
  for(cycle=0;cycle<14000;cycle=cycle+1) begin
   @(negedge clk);rng=advance(rng);
   if(kill) valid=0;
   else if(!valid || last_accept) begin
    valid=cycle<13000 && rng[31:30]!=0;
    if(valid) begin packet=instruction(seq);seq=seq+1;end
   end
   mul_ready=rng[24:23]!=0;
   rsp_valid=bus_pending && bus_delay==0;rsp_data=bus_raw;rsp_error=bus_error;
   req_ready=rng[27:26]!=0 && (!bus_pending || (rsp_valid && rsp_ready));
  end
  @(negedge clk);
  if(valid || ew!=er || bus_pending) $fatal(1,"test did not drain");
  if(buffered_turns<100 || overlap_requests<100 || faults<20 || muls<100 || stalls<100) $fatal(1,"insufficient coverage");
  $display("PASS memory overlap cycles=14000 accepts=%0d completions=%0d requests=%0d faults=%0d buffered=%0d overlap_load=%0d mul=%0d stalls=%0d",accepts,completions,requests,faults,buffered_turns,overlap_requests,muls,stalls);$finish;
 end
endmodule
