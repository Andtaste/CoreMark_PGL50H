// Fixed-latency, one-input-per-cycle multiply datapath.
// Partial products are captured on acceptance. Completion is buffered
// by the existing in-flight token; only the MEM head may consume a result.
module nc_mul_pipeline #(parameter REGISTER_CONSUME=0)(input wire clk,rst_n,clear,accept,
 input wire in_lane,output reg forward_lane,input wire[2:0] in_tag,input wire[1:0] operation,input wire[31:0] a,b,
 input wire[2:0] query_tag,input wire consume,output wire query_ready,output wire[31:0] query_data,
 output reg forward_valid,output reg[2:0] forward_tag,output reg[31:0] forward_data,
 output wire busy,output wire[3:0] next_forward_tag);
 reg lane1,lane2;reg v1,v2;reg[2:0] tag1,tag2;reg[1:0] op1,op2;
 wire[31:0] aa=a,bb=b;wire[1:0] op0=operation;
 wire signed[16:0] al=$signed({1'b0,aa[15:0]}),bl=$signed({1'b0,bb[15:0]});
 wire signed[16:0] ah=$signed({(op0==1 || op0==2) && aa[31],aa[31:16]});
 wire signed[16:0] bh=$signed({op0==1 && bb[31],bb[31:16]});
 wire signed[33:0] ll /* synthesis syn_dspstyle="block_mult" */;
 wire signed[33:0] lh /* synthesis syn_dspstyle="block_mult" */;
 wire signed[33:0] hl /* synthesis syn_dspstyle="block_mult" */;
 wire signed[33:0] hh /* synthesis syn_dspstyle="block_mult" */;
 assign ll=al*bl;assign lh=al*bh;assign hl=ah*bl;assign hh=ah*bh;
 reg signed[33:0] p_ll,p_lh,p_hl,p_hh;
 wire signed[34:0] middle=$signed({p_lh[33],p_lh})+$signed({p_hl[33],p_hl})+
                              $signed({19'b0,p_ll[31:16]});
 reg[31:0] low2,upper2,cross2;
 wire[31:0] completed=upper2+cross2;
 wire low_done=v1 && op1==0,high_done=v2 && op2!=0;
 assign next_forward_tag=low_done ? {tag1,lane1} : {tag2,lane2};
 wire[31:0] low_completed={middle[15:0],p_ll[15:0]};
 reg[31:0] results[0:7] /* synthesis syn_ramstyle="registers" */;
 reg[7:0] available;
 reg consume_q;reg[2:0] consume_tag_q;
 wire release_valid=REGISTER_CONSUME ? consume_q : consume;
 wire[2:0] release_tag=REGISTER_CONSUME ? consume_tag_q : query_tag;
 assign query_ready=available[query_tag];assign query_data=results[query_tag];
 assign busy=v1 || (v2 && op2!=0) || |available;
 always @(posedge clk) begin
  consume_tag_q<=query_tag;
  // Capture partial products immediately; token ownership follows acceptance.
  if(accept) begin lane1<=in_lane;p_ll<=ll;p_lh<=lh;p_hl<=hl;p_hh<=hh;op1<=operation;tag1<=in_tag;end
  if(v1) begin
   lane2<=lane1;low2<={middle[15:0],p_ll[15:0]};upper2<=p_hh[31:0];
   cross2<={{13{middle[34]}},middle[34:16]};op2<=op1;tag2<=tag1;
  end
  // These are parallel destination FFs for the same final value. The
  // broadcast has no token-indexed read mux before the EX operand network.
  // MUL low is already complete at the middle-sum register; do not send
  // it through the high-half adder stage. Both completions can be retained
  // in distinct token banks in the same cycle. A broadcast collision gives
  // low MUL priority; the other result remains available to ordered MEM/WB.
  if(high_done) results[tag2]<=completed;
  if(low_done) results[tag1]<=low_completed;
  if(low_done || high_done) begin
   forward_data<=low_done ? low_completed : completed;
   forward_tag<=low_done ? tag1 : tag2;forward_lane<=low_done ? lane1 : lane2;
  end
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin v1<=0;v2<=0;forward_valid<=0;available<=0;consume_q<=0;end
  else if(clear) begin v1<=0;v2<=0;forward_valid<=0;available<=0;consume_q<=0;end
  else begin
   v1<=accept;v2<=v1;forward_valid<=low_done || high_done;consume_q<=consume;
   if(release_valid) available[release_tag]<=0;
   if(high_done) available[tag2]<=1;
   if(low_done) available[tag1]<=1;
  end
 end
endmodule
