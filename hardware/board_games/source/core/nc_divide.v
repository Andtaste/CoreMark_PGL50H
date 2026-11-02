// Blocking DIV/REM only. Multiplication uses nc_mul_pipeline separately.
module nc_divide(input wire clk,rst_n,clear,start,consume,input wire[2:0] op,
 input wire[31:0] a,b,output wire done,output reg[31:0] result);
 reg[2:0] state,operation;reg[31:0] quotient,divisor;
 reg[32:0] remainder;reg[5:0] steps;reg neg_q,neg_r;
 wire[32:0] shifted={remainder[31:0],quotient[31]};
 wire subtract=shifted>={1'b0,divisor};
 wire[32:0] rem_next=subtract ? shifted-{1'b0,divisor} : shifted;
 wire[31:0] quo_next={quotient[30:0],subtract};
 assign done=state==6;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin state<=0;operation<=0;result<=0;quotient<=0;divisor<=0;
   remainder<=0;steps<=0;neg_q<=0;neg_r<=0;
  end else if(clear) state<=0;
  else case(state)
   0:if(start) begin
    operation<=op;quotient<=(!op[0] && a[31]) ? -a : a;
    divisor<=(!op[0] && b[31]) ? -b : b;
    neg_q<=!op[0] && (a[31]^b[31]);neg_r<=!op[0] && a[31];remainder<=0;steps<=0;
    if(b==0) begin result<=op[1] ? a : 32'hffffffff;state<=6;end
    else state<=4;
   end
   4:begin remainder<=rem_next;quotient<=quo_next;steps<=steps+1'b1;if(steps==31) state<=5;end
   5:begin result<=operation[1] ? (neg_r ? -remainder[31:0] : remainder[31:0]) :
                                            (neg_q ? -quotient : quotient);state<=6;end
   6:if(consume) state<=0;
   default:state<=0;
  endcase
 end
endmodule
