// EX has no physical RAM outputs and no combinational frontend control.
// Its complete result/transaction is captured by MEM before authorization.
module nc_execute(input wire clk,rst_n,clear,input wire valid,output wire ready,
 input wire[203:0] packet,input wire[18:0] control,output wire out_valid,input wire out_ready,
 output wire redirect_needed,output wire[31:0] redirect_target,
 output wire[276:0] out_packet);
 wire[3:0] kind;wire[31:0] pc,insn,a,b,imm,csr_old;wire[4:0] rd;
 wire wr,illegal,fetch_error;
 assign {kind,pc,insn,a,b,imm,csr_old,rd,wr,illegal,fetch_error}=packet;
 wire[2:0] f3=insn[14:12];
 wire[31:0] rhs=control[15] ? imm : b;
 wire[31:0] address=a+imm;
 wire[31:0] direct_target=pc+imm;
 wire[31:0] csr_operand=f3[2] ? {27'b0,insn[19:15]} : a;
 reg[31:0] result,next_pc,tval,csr_data;
 reg exception,csr_we,taken;
 reg[4:0] cause;
 wire md_done;wire[31:0] md_result;
 wire[31:0] sequential_pc=pc+32'd4;
 wire[31:0] indirect_target={address[31:1],1'b0};
 assign redirect_target=control[18] ? indirect_target : direct_target;
 // A direct target differs from PC+4 iff its signed immediate differs from
 // four, including modulo-32-bit wrap. This test runs before taken arrives.
 // JALR retains the actual target comparison, in parallel with PC selection.
 wire direct_change=imm!=32'd4;
 wire indirect_change=indirect_target!=sequential_pc;
 assign redirect_needed=!illegal && !fetch_error &&
  (((control[17] || (control[16] && taken)) && direct_change && !direct_target[1] && !direct_target[0]) ||
   (control[18] && indirect_change && !address[1]));
 wire branch_bad=control[18] ? address[1] : control[17] ? |direct_target[1:0] :
                 control[16] && (taken ? |direct_target[1:0] : |sequential_pc[1:0]);
 wire[31:0] branch_bad_value=(control[16] && !taken) ? sequential_pc : redirect_target;
 wire[31:0] add_value=a+(rhs^{32{control[13]}})+{31'b0,control[13]};
 wire[31:0] left_value=a<<rhs[4:0];
 wire signed[32:0] right_input={control[14] && a[31],a};
 wire[32:0] right_value=$signed(right_input)>>>rhs[4:0];
 // Parallel, registered one-hot enables replace nested instruction/opcode
 // muxes on the result path. No added execution stage or response bypass.
 wire[31:0] selected_result=
  ({32{control[0]}} & add_value) |
  ({32{control[1]}} & left_value) |
  ({32{control[2]}} & {31'b0,$signed(a)<$signed(rhs)}) |
  ({32{control[3]}} & {31'b0,a<rhs}) |
  ({32{control[4]}} & (a^rhs)) |
  ({32{control[5]}} & right_value[31:0]) |
  ({32{control[6]}} & (a|rhs)) |
  ({32{control[7]}} & (a&rhs)) |
  ({32{control[8]}} & imm) |
  ({32{control[9]}} & direct_target) |
  ({32{control[10]}} & sequential_pc) |
  ({32{control[11]}} & md_result) |
  ({32{control[12]}} & csr_old);
 wire is_md=kind==6 && !illegal && !fetch_error;
 assign out_valid=valid && (!is_md || md_done);
 assign ready=out_ready && (!is_md || md_done);
 nc_muldiv md(.clk(clk),.rst_n(rst_n),.clear(clear),.start(valid && is_md && !md_done),
  .consume(out_valid && out_ready && is_md),.op(f3),.a(a),.b(b),.done(md_done),.result(md_result));
 always @* begin
  result=selected_result;next_pc=sequential_pc;tval=0;csr_data=csr_old;exception=0;cause=0;csr_we=0;taken=0;
  case(f3)
   0:taken=a==b;1:taken=a!=b;4:taken=$signed(a)<$signed(b);
   5:taken=$signed(a)>=$signed(b);6:taken=a<b;7:taken=a>=b;default:;
  endcase
  case(kind)
   0:;
   1:if(taken) next_pc=direct_target;
   2:next_pc=direct_target;
   3:next_pc=indirect_target;
   4,5:begin
    if((f3[1:0]==2 && |address[1:0]) || (f3[1:0]==1 && address[0])) begin
     exception=1;cause=kind==5 ? 6 : 4;tval=address;
    end
   end
   6:;
   7:begin
    csr_we=f3[1:0]==1 || insn[19:15]!=0;
    case(f3[1:0]) 1:csr_data=csr_operand;2:csr_data=csr_old|csr_operand;
     3:csr_data=csr_old & ~csr_operand;default:;endcase
   end
   8:begin
    if(insn==32'h00000073) begin exception=1;cause=11;end
    if(insn==32'h00100073) begin exception=1;cause=3;tval=pc;end
   end
   default:;
  endcase
  if(branch_bad) begin exception=1;cause=0;tval=branch_bad_value;end
  if(illegal) begin exception=1;cause=2;tval=insn;end
  if(fetch_error) begin exception=1;cause=1;tval=pc;end
 end
 wire serial=kind>=7 || illegal || fetch_error;
 assign out_packet={pc,insn,next_pc,result,address,b,tval,csr_data,cause,rd,f3,kind,
                    wr,exception,csr_we,serial};
endmodule
