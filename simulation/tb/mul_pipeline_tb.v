`timescale 1ns/1ps
module mul_pipeline_tb;
 reg clk=0;always #5 clk=!clk;
 reg rst_n=0,clear=0,accept=0,consume=0;
 reg[2:0] in_tag=0,query_tag=0;reg[1:0] operation=0;reg[31:0] a=0,b=0;
 wire ready,fv,busy;wire[31:0] data,fd;wire[2:0] ft;
 nc_mul_pipeline dut(.clk(clk),.rst_n(rst_n),.clear(clear),.accept(accept),.consume(consume),
  .in_tag(in_tag),.operation(operation),.a(a),.b(b),.query_tag(query_tag),.query_ready(ready),.query_data(data),
  .forward_valid(fv),.forward_tag(ft),.forward_data(fd),.busy(busy));
 reg[7:0] reserved=0,available=0;reg[31:0] expected[0:7];
 reg[2:0] pv=0,pt[0:2];reg[1:0] po[0:2];reg[31:0] pr[0:2];
 reg[31:0] rng=32'h01835e72;reg completion,low_done,high_done;
 integer i,n,free_tag,read_tag,accepted=0,completed=0,cleared=0,streak=0,max_streak=0,collisions=0;
 function[31:0] reference(input[31:0] x,y,input[1:0] op);
  reg signed[63:0] sx,sy;reg[63:0] product;
  begin
   sx=(op==1 || op==2) ? {{32{x[31]}},x} : {32'b0,x};
   sy=op==1 ? {{32{y[31]}},y} : {32'b0,y};
   product=sx*sy;reference=op==0 ? product[31:0] : product[63:32];
  end
 endfunction
 function[31:0] edge_value(input integer k);
  case(k%8) 0:edge_value=0;1:edge_value=1;2:edge_value=32'h7fffffff;3:edge_value=32'h80000000;
   4:edge_value=32'hffffffff;5:edge_value=32'h0000ffff;6:edge_value=32'hffff0000;7:edge_value=32'h80000001;endcase
 endfunction
 initial begin
  repeat(3) @(negedge clk);rst_n=1;
  for(i=0;i<20016;i=i+1) begin
   @(negedge clk);rng=rng*32'd1664525+32'd1013904223;
   free_tag=-1;read_tag=-1;
   for(n=0;n<8;n=n+1) begin
    if(!reserved[(i+n)%8] && free_tag<0) free_tag=(i+n)%8;
    if(available[(i+n)%8] && read_tag<0) read_tag=(i+n)%8;
   end
   clear=i>=256 && i<20000 && i%127==126;
   accept=i<20000 && free_tag>=0 && (i<256 || rng[31:28]<12);
   consume=read_tag>=0 && (i<256 || i>=20000 || rng[27:24]<8);
   in_tag=free_tag<0 ? 0 : free_tag;query_tag=read_tag<0 ? rng[2:0] : read_tag;
   operation=i<256 ? i/64 : rng[23:22];
   a=i<256 ? edge_value(i) : rng;
   b=i<256 ? edge_value(i/8) : (rng^32'hb73a0e91)*32'd1103515245;
   @(posedge clk);
   if(ready!==available[query_tag] || (ready && data!==expected[query_tag])) $fatal(1,"held result mismatch i=%0d",i);
   low_done=pv[1] && po[1]==0 && !clear;high_done=pv[2] && po[2]!=0 && !clear;
   completion=low_done || high_done;
   #1;
   if(clear) begin reserved=0;available=0;pv=0;cleared=cleared+1;streak=0;end
   else begin
    if(consume) begin reserved[query_tag]=0;available[query_tag]=0;end
    if(high_done) begin
     if(available[pt[2]]) $fatal(1,"overwriting unconsumed result");
     available[pt[2]]=1;expected[pt[2]]=pr[2];completed=completed+1;
    end
    if(low_done) begin
     if(available[pt[1]]) $fatal(1,"overwriting unconsumed low result");
     available[pt[1]]=1;expected[pt[1]]=pr[1];completed=completed+1;
    end
    if(low_done && high_done) collisions=collisions+1;
    if(accept) begin reserved[in_tag]=1;accepted=accepted+1;streak=streak+1;end else streak=0;
    if(streak>max_streak) max_streak=streak;
   end
   if(fv!==completion || (completion && (ft!==(low_done ? pt[1] : pt[2]) || fd!==(low_done ? pr[1] : pr[2]))))
    $fatal(1,"multiply/latency mismatch i=%0d tag=%0d result=%h expected=%h",i,ft,fd,pr[2]);
   if(!clear) begin
    for(n=2;n>0;n=n-1) begin pt[n]=pt[n-1];pr[n]=pr[n-1];po[n]=po[n-1];end
    pt[0]=in_tag;pr[0]=reference(a,b,operation);po[0]=operation;pv={pv[1:0],accept};
   end
   if(ready!==available[query_tag] || (ready && data!==expected[query_tag])) $fatal(1,"post-edge result mismatch");
   if(busy!==(reserved!=0)) $fatal(1,"pipeline occupancy mismatch");
  end
  if(reserved!=0 || available!=0 || accepted<4000 || completed<4000 || max_streak<16 || cleared==0 || collisions==0)
   $fatal(1,"missing multiply coverage or drain");
  $display("PASS multiply pipeline accepted=%0d completed=%0d clears=%0d max_accept_streak=%0d dual_completion=%0d",accepted,completed,cleared,max_streak,collisions);$finish;
 end
endmodule
