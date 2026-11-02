// Original RV32IM/Zicsr decoder. Classes: ALU=0, branch=1, JAL=2,
// JALR=3, load=4, store=5, M=6, CSR=7, system=8, fence=9.
module nc_decode(input wire[31:0] insn,
 output reg[3:0] kind,output reg[31:0] imm,
 output reg use1,use2,write_rd,serial,illegal,output reg[18:0] control,
 output wire[4:0] rs1,rs2,rd,
 input wire csr_exists,csr_writable);
 wire[6:0] op=insn[6:0],f7=insn[31:25];
 wire[2:0] f3=insn[14:12];
 assign rs1=insn[19:15];assign rs2=insn[24:20];assign rd=insn[11:7];
 always @* begin
  kind=0;imm={{20{insn[31]}},insn[31:20]};
  use1=0;use2=0;write_rd=0;serial=0;illegal=0;
  case(op)
   7'h37,7'h17:begin imm={insn[31:12],12'b0};write_rd=1;end
   7'h13:begin
    use1=1;write_rd=1;
    if(f3==1 && f7!=0) illegal=1;
    if(f3==5 && f7!=0 && f7!=7'h20) illegal=1;
   end
   7'h33:begin
    use1=1;use2=1;write_rd=1;
    if(f7==1) kind=6;
    else if(f7!=0 && !(f7==7'h20 && (f3==0 || f3==5))) illegal=1;
   end
   7'h63:begin
    kind=1;use1=1;use2=1;
    imm={{19{insn[31]}},insn[31],insn[7],insn[30:25],insn[11:8],1'b0};
    if(f3==2 || f3==3) illegal=1;
   end
   7'h6f:begin kind=2;write_rd=1;
    imm={{11{insn[31]}},insn[31],insn[19:12],insn[20],insn[30:21],1'b0};end
   7'h67:begin kind=3;use1=1;write_rd=1;if(f3!=0) illegal=1;end
   7'h03:begin kind=4;use1=1;write_rd=1;
    if(!(f3==0 || f3==1 || f3==2 || f3==4 || f3==5)) illegal=1;end
   7'h23:begin kind=5;use1=1;use2=1;
    imm={{20{insn[31]}},insn[31:25],insn[11:7]};if(f3>2) illegal=1;end
   7'h73:begin
    serial=1;
    if(f3==0) begin kind=8;
     if(insn!=32'h00000073 && insn!=32'h00100073 &&
        insn!=32'h30200073 && insn!=32'h10500073) illegal=1;
    end else begin
     kind=7;use1=!f3[2];write_rd=1;
     if(f3==4 || !csr_exists ||
        ((f3[1:0]==1 || rs1!=0) && !csr_writable)) illegal=1;
    end
   end
   7'h0f:begin kind=9;serial=1;if(f3!=0 && f3!=1) illegal=1;end
   default:illegal=1;
  endcase
  if(illegal) begin serial=1;write_rd=0;use1=0;use2=0;end
  // Register one-hot result enables with ID/EX. No late kind/funct mux
  // cascade after the barrel shifter. Flags: sub, arithmetic, imm, B/J/JR.
  control=0;
  case(kind)
   0:begin
    if(op==7'h37) control[8]=1;
    else if(op==7'h17) control[9]=1;
    else control[f3]=1;
    control[13]=op==7'h33 && f3==0 && insn[30];
    control[14]=insn[30];control[15]=op==7'h13;
   end
   1:control[16]=1;
   2:begin control[10]=1;control[17]=1;end
   3:begin control[10]=1;control[18]=1;end
   6:control[11]=1;
   7:control[12]=1;
   default:;
  endcase
 end
endmodule
