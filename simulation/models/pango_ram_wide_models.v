// Functional asymmetric TDP model; synthesized design uses generated Pango IP.
module ram1_tdp(input wire a_clk,a_rst,a_clk_en,a_wr_en,input wire[12:0] a_addr,
 input wire[63:0] a_wr_data,input wire[7:0] a_wr_byte_en,output reg[63:0] a_rd_data,
 input wire b_clk,b_rst,b_clk_en,b_wr_en,input wire[13:0] b_addr,
 input wire[31:0] b_wr_data,input wire[3:0] b_wr_byte_en,output reg[31:0] b_rd_data);
 reg[31:0] mem[0:16383];integer i,j,k;reg[4095:0] image;
 initial begin
  for(i=0;i<16384;i=i+1) mem[i]=0;
  if($value$plusargs("image=%s",image)) $readmemh(image,mem);

 end
 always @(posedge a_clk) if(a_clk_en) begin
  a_rd_data<={mem[{a_addr,1'b1}],mem[{a_addr,1'b0}]};
  for(j=0;j<8;j=j+1) if(a_wr_en && a_wr_byte_en[j]) mem[{a_addr,1'b0}+(j/4)][8*(j%4)+:8]<=a_wr_data[8*j+:8];
 end
 always @(posedge b_clk) if(b_clk_en) begin
  b_rd_data<=mem[b_addr];for(k=0;k<4;k=k+1) if(b_wr_en && b_wr_byte_en[k]) mem[b_addr][8*k+:8]<=b_wr_data[8*k+:8];
 end
endmodule
module ram2_tdp(input wire a_clk,a_rst,a_clk_en,a_wr_en,input wire[11:0] a_addr,
 input wire[63:0] a_wr_data,input wire[7:0] a_wr_byte_en,output reg[63:0] a_rd_data,
 input wire b_clk,b_rst,b_clk_en,b_wr_en,input wire[12:0] b_addr,
 input wire[31:0] b_wr_data,input wire[3:0] b_wr_byte_en,output reg[31:0] b_rd_data);
 reg[31:0] mem[0:8191];integer i,j,k;reg[4095:0] image;
 initial begin
  for(i=0;i<8192;i=i+1) mem[i]=0;

 end
 always @(posedge a_clk) if(a_clk_en) begin
  a_rd_data<={mem[{a_addr,1'b1}],mem[{a_addr,1'b0}]};
  for(j=0;j<8;j=j+1) if(a_wr_en && a_wr_byte_en[j]) mem[{a_addr,1'b0}+(j/4)][8*(j%4)+:8]<=a_wr_data[8*j+:8];
 end
 always @(posedge b_clk) if(b_clk_en) begin
  b_rd_data<=mem[b_addr];for(k=0;k<4;k=k+1) if(b_wr_en && b_wr_byte_en[k]) mem[b_addr][8*k+:8]<=b_wr_data[8*k+:8];
 end
endmodule
