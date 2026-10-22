`timescale 1ns/1ps
module btb_tb;
 reg clk=0;always #5 clk=!clk;
 reg rst_n=0,flush=0,uv=0,ub=0,uc=0,ut=0;
 reg[31:0] pc=0,upc=0,target=0;wire[31:0] prediction;
 nc_btb dut(.clk(clk),.rst_n(rst_n),.flush(flush),.lookup_pc(pc),.prediction(prediction),
  .update_valid(uv),.update_branch(ub),.update_conditional(uc),.update_taken(ut),
  .update_pc(upc),.update_target(target));
 reg mv[0:63],mc[0:63];reg[23:0] mt[0:63];reg[29:0] md[0:63];
 integer state[0:63][0:1];reg history[0:63];integer i,j,k,r,w,hits=0,allocations=0,invalidations=0,clears=0;
 reg[31:0] rng=32'h6418c75a;reg expected_hit,expected_taken;
 function[31:0] advance(input[31:0] x);advance=x*32'd1664525+32'd1013904223;endfunction
 initial begin
  for(j=0;j<64;j=j+1) begin mv[j]=0;state[j][0]=0;state[j][1]=0;history[j]=0;mc[j]=0;mt[j]=0;md[j]=0;end
  repeat(3) @(negedge clk);rst_n=1;
  for(i=0;i<20000;i=i+1) begin
   @(negedge clk);rng=advance(rng);
   uv=rng[31:28]!=0;ub=rng[27:25]!=0;uc=rng[24];ut=rng[23];flush=i%197==196;
   w=rng[5:0];upc={20'h00100,rng[11:8],6'b0,2'b0}+(w<<2);
   target={rng[29:0],2'b0};
   r=i%2==0 ? w : rng[21:16];pc=mv[r] ? {mt[r],r[5:0],2'b0} : (32'h10000+(r<<2));
   // Force both saturation ends and both weak-state crossings at eight
   // indices before the random collision/update/flush sequence.
   if(i<256) begin
    w=i/32;upc=32'h10000+(w<<2);pc=upc;
    uv=1;ub=1;uc=1;ut=i%32<16;flush=0;
   end
   // After the saturation sweep, learn both alternating outcome contexts.
   if(i>=256 && i<512) begin
    w=8+(i-256)/32;upc=32'h10000+(w<<2);pc=upc;
    uv=1;ub=1;uc=1;ut=i%2;flush=0;
   end
   @(posedge clk);#1;
   if(flush) begin for(j=0;j<64;j=j+1) mv[j]=0;clears=clears+1;end
   else if(uv) begin
    if(ub) begin
     if(!mv[w] || mt[w]!=upc[31:8]) begin
      state[w][0]=ut ? 2 : 1;state[w][1]=ut ? 2 : 1;allocations=allocations+1;
     end
     else case(state[w][history[w]])
      0:state[w][history[w]]=ut ? 1 : 0;
      1:state[w][history[w]]=ut ? 2 : 0;
      2:state[w][history[w]]=ut ? 3 : 1;
      3:state[w][history[w]]=ut ? 3 : 2;
     endcase
     history[w]=uc && ut;
     if(!uc) begin state[w][0]=3;state[w][1]=3;end
     mv[w]=1;mt[w]=upc[31:8];md[w]=target[31:2];mc[w]=uc;
    end else if(mv[w] && mt[w]==upc[31:8]) begin mv[w]=0;invalidations=invalidations+1;end
   end
   // Scan all indices, including tag collisions, while writes are idle.
   for(k=0;k<2;k=k+1) begin
    if(k==1) pc={upc[31:8]^24'h100,w[5:0],2'b0};
    #1;r=pc[7:2];expected_hit=mv[r] && mt[r]==pc[31:8];
    expected_taken=expected_hit && (!mc[r] || state[r][history[r]]>=2);
    if(prediction[31]!==expected_hit || prediction[30]!==expected_taken ||
       (expected_hit && prediction[29:0]!==md[r])) $fatal(1,"BTB model mismatch i=%0d pc=%h",i,pc);
    if(expected_hit) hits=hits+1;
   end
  end
  if(hits==0 || allocations==0 || clears==0 || invalidations==0) $fatal(1,"BTB missing coverage");
  $display("PASS BTB model updates=20000 hits=%0d allocations=%0d invalidations=%0d flushes=%0d",hits,allocations,invalidations,clears);$finish;
 end
endmodule
