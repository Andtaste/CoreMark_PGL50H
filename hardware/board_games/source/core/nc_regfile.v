// Four reads / two writes, using two reset-free single-writer RAM banks.
// Last-writer bits are FFs; data RAMs infer distributed RAM. No read-through
// writeback mux. ID dependency tracking handles writes on the sampling edge.
module nc_regfile(input wire clk,input wire we,we1,input wire[4:0] wa,wa1,
 input wire[31:0] wd,wd1,input wire[4:0] ra,rb,rc,rd,output wire[31:0] a,b,c,d);
 reg[31:0] bank0[0:31] /* synthesis syn_ramstyle="lut_ram" */;
 reg[31:0] bank1[0:31] /* synthesis syn_ramstyle="lut_ram" */;
 reg[31:0] owner;
 always @(posedge clk) begin
  if(we && wa!=0) begin bank0[wa]<=wd;owner[wa]<=0;end
  if(we1 && wa1!=0) begin bank1[wa1]<=wd1;owner[wa1]<=1;end
 end
 assign a=ra==0 ? 0 : owner[ra] ? bank1[ra] : bank0[ra];
 assign b=rb==0 ? 0 : owner[rb] ? bank1[rb] : bank0[rb];
 assign c=rc==0 ? 0 : owner[rc] ? bank1[rc] : bank0[rc];
 assign d=rd==0 ? 0 : owner[rd] ? bank1[rd] : bank0[rd];
 // Simulation-only architectural view for inherited ISA test monitors.
 // synthesis translate_off
 wire[31:0] regs[0:31];genvar r;
 generate for(r=0;r<32;r=r+1) begin:view
  assign regs[r]=r==0 ? 0 : owner[r] ? bank1[r] : bank0[r];
 end endgenerate
 // synthesis translate_on
endmodule
