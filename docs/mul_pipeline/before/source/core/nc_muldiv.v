// Original blocking EX arithmetic unit. Reset-free operand/product registers
// let PDS absorb multipliers into Pango APM input/output registers.
// No combinational operand bypass into a DSP and no raw DSP output to WB.
module nc_muldiv(input wire clk,rst_n,clear,start,consume,input wire[2:0] op,
 input wire[31:0] a,b,output wire done,output reg[31:0] result);
 reg [2:0] state,operation;
 reg [31:0] aa,bb,p00,p01,p10,p11;
 reg [63:0] product;
 reg [31:0] quotient,divisor;
 reg [32:0] remainder;
 reg [5:0] steps;
 reg neg_q,neg_r;
 wire [31:0] m00 /* synthesis syn_dspstyle = "block_mult" */;
 wire [31:0] m01 /* synthesis syn_dspstyle = "block_mult" */;
 wire [31:0] m10 /* synthesis syn_dspstyle = "block_mult" */;
 wire [31:0] m11 /* synthesis syn_dspstyle = "block_mult" */;
 assign m00=aa[15:0]*bb[15:0];assign m01=aa[15:0]*bb[31:16];
 assign m10=aa[31:16]*bb[15:0];assign m11=aa[31:16]*bb[31:16];
 wire [32:0] shifted={remainder[31:0],quotient[31]};
 wire subtract=shifted>={1'b0,divisor};
 wire [32:0] rem_next=subtract ? shifted-{1'b0,divisor} : shifted;
 wire [31:0] quo_next={quotient[30:0],subtract};
 assign done=state==6;
 always @(posedge clk) begin
  if(state==0 && start) begin aa<=a;bb<=b;end
  if(state==1) begin p00<=m00;p01<=m01;p10<=m10;p11<=m11;end
  if(state==2) product<={p11,p00}+{16'b0,p01,16'b0}+{16'b0,p10,16'b0};
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin state<=0;operation<=0;result<=0;quotient<=0;divisor<=0;
   remainder<=0;steps<=0;neg_q<=0;neg_r<=0;end
  else if(clear) state<=0;
  else case(state)
   0:if(start) begin
    operation<=op;
    if(!op[2]) state<=1;
    else begin
     quotient<=(!op[0] && a[31]) ? -a : a;
     divisor<=(!op[0] && b[31]) ? -b : b;
     neg_q<=!op[0] && (a[31]^b[31]);neg_r<=!op[0] && a[31];
     remainder<=0;steps<=0;
     if(b==0) begin result<=op[1] ? a : 32'hffffffff;state<=6;end
     else state<=4;
    end
   end
   1:state<=2;
   // MUL only needs the low 32 bits. Finish at this registered partial-
   // product adder; the high-half/signed correction stage is unnecessary.
   2:if(operation==0) begin
    result<=p00+{p01[15:0],16'b0}+{p10[15:0],16'b0};state<=6;
   end else state<=3;
   3:begin
    if(operation==0) result<=product[31:0];
    else result<=product[63:32]-((operation==1 || operation==2) && aa[31] ? bb : 32'b0)
                                         -(operation==1 && bb[31] ? aa : 32'b0);
    state<=6;
   end
   4:begin
    remainder<=rem_next;quotient<=quo_next;steps<=steps+1'b1;
    if(steps==31) state<=5;
   end
   5:begin result<=operation[1] ? (neg_r ? -remainder[31:0] : remainder[31:0]) :
                                             (neg_q ? -quotient : quotient);state<=6;end
   6:if(consume) state<=0;
   default:state<=0;
  endcase
 end
endmodule
