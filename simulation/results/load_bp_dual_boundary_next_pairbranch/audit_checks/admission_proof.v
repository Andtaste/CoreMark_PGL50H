module admission_proof(input[31:0] insn,output equal);
 function[8:0] classify_parts;
  input[31:0] insn;
  reg[6:0] op,f7;reg[2:0] f3;
  reg upper,imm_op,reg_op,zero_f7,alt_f7;
  reg base_alu,zero_alu,alt_alu,memory_op,multiply_op;
  begin
   op=insn[6:0];f3=insn[14:12];f7=insn[31:25];
   upper=(op & 7'h5f)==7'h17;
   imm_op=op==7'h13;reg_op=op==7'h33;
   zero_f7=f7==0;alt_f7=f7==7'h20;
   // Non-shift immediates do not interpret upper immediate bits as f7.
   base_alu=upper || (imm_op && (f3[1] || !f3[0]));
   zero_alu=(imm_op || reg_op) && zero_f7;
   alt_alu=alt_f7 && ((imm_op && f3==5) || (reg_op && (f3==0 || f3==5)));
   memory_op=(op==7'h03 && (!f3[1] || f3==2)) ||
             (op==7'h23 && !f3[2] && f3[1:0]!=3);
   multiply_op=reg_op && f7==1 && !f3[2];
   classify_parts={((1 && op==7'h63 && f3!=2 && f3!=3 && !insn[8]) || (1 && multiply_op)),multiply_op,memory_op,alt_alu,zero_alu,base_alu,
                   op!=7'h23 && op!=7'h63,reg_op || op==7'h63,imm_op || reg_op || op==7'h63};
  end
 endfunction
 wire[8:0] p=classify_parts(insn);wire allowed=|p[5:3] || p[8];wire[3:0] kind;wire illegal,wr,u1,u2,serial;
 nc_decode d(.insn(insn),.kind(kind),.imm(),.use1(u1),.use2(u2),.write_rd(wr),.serial(serial),.illegal(illegal),.control(),.rs1(),.rs2(),.rd(),.csr_exists(1'b0),.csr_writable(1'b0));
 assign equal=!allowed || (!illegal && !serial && wr==p[2] && u1==p[0] && u2==p[1] && ((kind==1)==insn[6]) && (kind==0 || kind==1 || (kind==6 && !insn[14])));
 endmodule
