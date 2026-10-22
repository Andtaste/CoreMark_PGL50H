`timescale 1ns/1ps
module wide_ip_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,ae=0,be=0,bw=0;reg[12:0] aa=0;reg[13:0] ba=0;reg[31:0] wd=0;reg[3:0] mask=0;
 wire[63:0] ar;wire[31:0] br;
 ram1_tdp ram(.a_clk(clk),.a_rst(reset),.a_clk_en(ae),.a_addr(aa),.a_wr_data(64'b0),.a_wr_en(1'b0),.a_wr_byte_en(8'b0),.a_rd_data(ar),
  .b_clk(clk),.b_rst(reset),.b_clk_en(be),.b_addr(ba),.b_wr_data(wd),.b_wr_en(bw),.b_wr_byte_en(mask),.b_rd_data(br));
 reg[31:0] reference[0:16383];reg[4095:0] image;
 reg[31:0] rng=32'h9175943,old_b;reg[63:0] old_a,held_a,held_b;
 integer i,j,checks=0;
 initial begin
  if(!$value$plusargs("image=%s",image)) $fatal(1,"Missing fixed image");$readmemh(image,reference);
  repeat(4) @(negedge clk);aa=13'h1555;ba=14'h2aaa;bw=1;mask=15;
  @(negedge clk);reset=0;bw=0;
  // Complete image readback checks generator initialization, port width
  // ratio, word order and every cascade boundary against the 32-bit image.
  for(i=0;i<8192;i=i+1) begin
   aa=i;ae=1;be=1;ba=2*i;
   @(posedge clk);#2;
   if(ar!=={reference[2*i+1],reference[2*i]} || br!==reference[2*i]) $fatal(1,"Generated IP init/width mapping mismatch index=%0d A=%h B=%h expectedB=%h",i,ar,br,reference[2*i]);
   checks=checks+2;@(negedge clk);
  end
  for(i=0;i<6000;i=i+1) begin
   rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
   aa=rng[12:0];ba=rng[26:13];wd=rng;mask=rng[4:1];ae=rng[0];be=rng[1];bw=rng[2];
   // Bus prevents read-A / write-B collisions in the same 64-bit row.
   if(be && bw && aa==ba[13:1]) ae=0;
   old_a={reference[{aa,1'b1}],reference[{aa,1'b0}]};old_b=reference[ba];held_a=ar;held_b=br;
   @(posedge clk);#2;
   if((ae && ar!==old_a) || (!ae && ar!==held_a) || (be && br!==old_b) || (!be && br!==held_b[31:0])) $fatal(1,"Generated IP read/enable semantics mismatch");
   if(be && bw) for(j=0;j<4;j=j+1) if(mask[j]) reference[ba][8*j+:8]=wd[8*j+:8];
   checks=checks+2;@(negedge clk);
  end
  ae=1;be=0;
  for(i=0;i<8192;i=i+1) begin
   aa=i;@(posedge clk);#2;
   if(ar!=={reference[2*i+1],reference[2*i]}) $fatal(1,"Generated IP B-write/A-read coherence mismatch index=%0d",i);
   checks=checks+1;@(negedge clk);
  end
  $display("PASS generated A64/B32 IP initialization/bytewrites/coherence checks=%0d",checks);$finish;
 end
endmodule
