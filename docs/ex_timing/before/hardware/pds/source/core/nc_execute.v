// EX has no physical RAM outputs and no combinational frontend control.
// Its complete result/transaction is captured by MEM before authorization.
module nc_execute(input wire clk,rst_n,clear,input wire valid,output wire ready,
 input wire[203:0] packet,output wire out_valid,input wire out_ready,
 output wire[276:0] out_packet);
 wire[3:0] kind;wire[31:0] pc,insn,a,b,imm,csr_old;wire[4:0] rd;
 wire wr,illegal,fetch_error;
 assign {kind,pc,insn,a,b,imm,csr_old,rd,wr,illegal,fetch_error}=packet;
 wire[2:0] f3=insn[14:12];
 wire[31:0] rhs=insn[6:0]==7'h13 ? imm : b;
 wire[31:0] address=a+imm;
 wire[31:0] direct_target=pc+imm;
 wire[31:0] csr_operand=f3[2] ? {27'b0,insn[19:15]} : a;
 reg[31:0] result,next_pc,tval,csr_data;
 reg exception,csr_we,taken;
 reg[4:0] cause;
 wire md_done;wire[31:0] md_result;
 wire is_md=kind==6 && !illegal && !fetch_error;
 assign out_valid=valid && (!is_md || md_done);
 assign ready=out_ready && (!is_md || md_done);
 nc_muldiv md(.clk(clk),.rst_n(rst_n),.clear(clear),.start(valid && is_md && !md_done),
  .consume(out_valid && out_ready && is_md),.op(f3),.a(a),.b(b),.done(md_done),.result(md_result));
 always @* begin
  result=0;next_pc=pc+4;tval=0;csr_data=csr_old;exception=0;cause=0;csr_we=0;taken=0;
  case(f3)
   0:taken=a==b;1:taken=a!=b;4:taken=$signed(a)<$signed(b);
   5:taken=$signed(a)>=$signed(b);6:taken=a<b;7:taken=a>=b;default:;
  endcase
  case(kind)
   0:begin
    if(insn[6:0]==7'h37) result=imm;
    else if(insn[6:0]==7'h17) result=direct_target;
    else case(f3)
     0:result=(insn[6:0]==7'h33 && insn[30]) ? a-rhs : a+rhs;
     1:result=a<<rhs[4:0];2:result={31'b0,$signed(a)<$signed(rhs)};
     3:result={31'b0,a<rhs};4:result=a^rhs;
     5:begin if(insn[30]) result=$signed(a)>>>rhs[4:0];else result=a>>rhs[4:0];end
     6:result=a|rhs;7:result=a&rhs;
    endcase
   end
   1:if(taken) next_pc=direct_target;
   2:begin result=pc+4;next_pc=direct_target;end
   3:begin result=pc+4;next_pc={address[31:1],1'b0};end
   4,5:begin
    if((f3[1:0]==2 && |address[1:0]) || (f3[1:0]==1 && address[0])) begin
     exception=1;cause=kind==5 ? 6 : 4;tval=address;
    end
   end
   6:result=md_result;
   7:begin
    result=csr_old;csr_we=f3[1:0]==1 || insn[19:15]!=0;
    case(f3[1:0]) 1:csr_data=csr_operand;2:csr_data=csr_old|csr_operand;
     3:csr_data=csr_old & ~csr_operand;default:;endcase
   end
   8:begin
    if(insn==32'h00000073) begin exception=1;cause=11;end
    if(insn==32'h00100073) begin exception=1;cause=3;tval=pc;end
   end
   default:;
  endcase
  if(kind>=1 && kind<=3 && |next_pc[1:0]) begin exception=1;cause=0;tval=next_pc;end
  if(illegal) begin exception=1;cause=2;tval=insn;end
  if(fetch_error) begin exception=1;cause=1;tval=pc;end
 end
 wire serial=kind>=7 || illegal || fetch_error;
 assign out_packet={pc,insn,next_pc,result,address,b,tval,csr_data,cause,rd,f3,kind,
                    wr,exception,csr_we,serial};
endmodule
