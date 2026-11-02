// 96KiB: original 64KiB plus 32KiB tail. Registered owner follows RAM latency.
module nc_code_ram(
 input a_clk,a_rst,a_clk_en,a_wr_en,input[13:0] a_addr,
 input[63:0] a_wr_data,input[7:0] a_wr_byte_en,output[63:0] a_rd_data,
 input b_clk,b_rst,b_clk_en,b_wr_en,input[13:0] b_addr,
 input[63:0] b_wr_data,input[7:0] b_wr_byte_en,output[63:0] b_rd_data);
 reg a_tail,b_tail;wire[63:0] a0,a1,b0,b1;
 always @(posedge a_clk)if(a_rst)a_tail<=0;else if(a_clk_en)a_tail<=a_addr[13];
 always @(posedge b_clk)if(b_rst)b_tail<=0;else if(b_clk_en)b_tail<=b_addr[13];
 assign a_rd_data=a_tail?a1:a0;assign b_rd_data=b_tail?b1:b0;
 ram1_tdp base(.a_clk(a_clk),.a_rst(a_rst),.a_clk_en(a_clk_en&&!a_addr[13]),.a_addr(a_addr[12:0]),
 .a_wr_en(a_wr_en),.a_wr_data(a_wr_data),.a_wr_byte_en(a_wr_byte_en),.a_rd_data(a0),
 .b_clk(b_clk),.b_rst(b_rst),.b_clk_en(b_clk_en&&!b_addr[13]),.b_addr(b_addr[12:0]),
 .b_wr_en(b_wr_en),.b_wr_data(b_wr_data),.b_wr_byte_en(b_wr_byte_en),.b_rd_data(b0));
 ram3_tdp tail(.a_clk(a_clk),.a_rst(a_rst),.a_clk_en(a_clk_en&&a_addr[13]&&!a_addr[12]),.a_addr(a_addr[11:0]),
 .a_wr_en(a_wr_en),.a_wr_data(a_wr_data),.a_wr_byte_en(a_wr_byte_en),.a_rd_data(a1),
 .b_clk(b_clk),.b_rst(b_rst),.b_clk_en(b_clk_en&&b_addr[13]&&!b_addr[12]),.b_addr(b_addr[11:0]),
 .b_wr_en(b_wr_en),.b_wr_data(b_wr_data),.b_wr_byte_en(b_wr_byte_en),.b_rd_data(b1));
endmodule
