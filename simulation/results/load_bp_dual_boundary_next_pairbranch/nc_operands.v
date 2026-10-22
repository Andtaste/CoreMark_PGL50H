// Two-entry in-order ID/EX boundary, with tagged operand forwarding.
// Only the head executes. Both slots remember broadcasts during stalls.
module nc_operands(input wire clk,rst_n,clear,
 input wire in_valid,output wire in_ready,input wire[203:0] in_packet,input wire[2:0] in_tag,
 input wire[223:0] in_side,output wire[223:0] out_side,
 input wire[18:0] in_control,output wire[18:0] out_control,
 input wire[31:0] in_prediction,output wire[31:0] out_prediction,
 input wire wait_a,wait_b,input wire[3:0] tag_a,tag_b,
 input wire wait_c,wait_d,input wire[3:0] tag_c,tag_d,
 input wire[2:0] next_f_tag,next_w_tag,input wire[3:0] next_m_tag,
 input wire f_valid,input wire[3:0] f_tag,input wire[31:0] f_data,
 input wire w_valid,input wire[3:0] w_tag,input wire[31:0] w_data,
 input wire m_valid,input wire[3:0] m_tag,input wire[31:0] m_data,
 output wire out_valid,input wire out_ready,output wire[203:0] out_packet,output wire[2:0] out_tag,
 input wire f1_valid,w1_valid,input wire[3:0] f1_tag,w1_tag,input wire[31:0] f1_data,w1_data,
 output wire occupied);
 reg[223:0] side[0:1];
 reg[3:0] dep_c[0:1],dep_d[0:1];reg[1:0] wc,wd;
 wire[1:0] available_c,available_d;wire[31:0] selected_c[0:1],selected_d[0:1];
 assign out_side={side[rd][223:136],selected_c[rd],selected_d[rd],side[rd][71:0]};
 reg[203:0] payload[0:1];reg[2:0] token[0:1];reg[3:0] dep_a[0:1],dep_b[0:1];
 reg[18:0] controls[0:1];assign out_control=controls[rd];
 reg[31:0] predictions[0:1];assign out_prediction=predictions[rd];
 reg[31:0] va[0:1],vb[0:1];reg[1:0] wa,wb;reg rd,wr;reg[1:0] count;
 wire[1:0] hit_fa,hit_fb,hit_wa,hit_wb,available_a,available_b;
 wire[1:0] hit_ma,hit_mb,hit_f1a,hit_f1b,hit_w1a,hit_w1b;
 wire[31:0] selected_va[0:1],selected_vb[0:1];
 reg[1:0] sf_a;
 reg[1:0] sf1_a;
 reg[1:0] sm_a;
 reg[1:0] sw_a;
 reg[1:0] sw1_a;
 reg[1:0] sf_b;
 reg[1:0] sf1_b;
 reg[1:0] sm_b;
 reg[1:0] sw_b;
 reg[1:0] sw1_b;
 reg[1:0] sf_c;
 reg[1:0] sf1_c;
 reg[1:0] sm_c;
 reg[1:0] sw_c;
 reg[1:0] sw1_c;
 reg[1:0] sf_d;
 reg[1:0] sf1_d;
 reg[1:0] sm_d;
 reg[1:0] sw_d;
 reg[1:0] sw1_d;
 genvar s;
 generate for(s=0;s<2;s=s+1) begin:slot_forward
  // Match each physical slot before selecting the queue head. These same
  // local matches feed its operand capture, without a dynamic-tag mux.
  assign hit_fa[s]=sf_a[s] && f_valid;
  assign hit_fb[s]=sf_b[s] && f_valid;
  assign hit_wa[s]=sw_a[s] && w_valid;
  assign hit_wb[s]=sw_b[s] && w_valid;
  assign hit_ma[s]=sm_a[s] && m_valid;assign hit_mb[s]=sm_b[s] && m_valid;
  assign hit_f1a[s]=sf1_a[s] && f1_valid;assign hit_w1a[s]=sw1_a[s] && w1_valid;
  // Exclusive priority masks preserve F > F1 > M > W > W1.
  // The W1 fall-through also preserves the old value on unavailable cycles.
  wire use_a_f=wa[s] && hit_fa[s];
  wire use_a_f1=wa[s] && !hit_fa[s] && hit_f1a[s];
  wire use_a_m=wa[s] && !(hit_fa[s] || hit_f1a[s]) && hit_ma[s];
  wire use_a_w=wa[s] && !(hit_fa[s] || hit_f1a[s] || hit_ma[s]) && hit_wa[s];
  wire use_a_w1=wa[s] && !(hit_fa[s] || hit_f1a[s] || hit_ma[s] || hit_wa[s]);
  assign selected_va[s]=({32{!wa[s]}} & va[s]) |
   ({32{use_a_f}} & f_data) | ({32{use_a_f1}} & f1_data) |
   ({32{use_a_m}} & m_data) | ({32{use_a_w}} & w_data) |
   ({32{use_a_w1}} & w1_data);
  assign hit_f1b[s]=sf1_b[s] && f1_valid;assign hit_w1b[s]=sw1_b[s] && w1_valid;
  // Exclusive priority masks preserve F > F1 > M > W > W1.
  // The W1 fall-through also preserves the old value on unavailable cycles.
  wire use_b_f=wb[s] && hit_fb[s];
  wire use_b_f1=wb[s] && !hit_fb[s] && hit_f1b[s];
  wire use_b_m=wb[s] && !(hit_fb[s] || hit_f1b[s]) && hit_mb[s];
  wire use_b_w=wb[s] && !(hit_fb[s] || hit_f1b[s] || hit_mb[s]) && hit_wb[s];
  wire use_b_w1=wb[s] && !(hit_fb[s] || hit_f1b[s] || hit_mb[s] || hit_wb[s]);
  assign selected_vb[s]=({32{!wb[s]}} & vb[s]) |
   ({32{use_b_f}} & f_data) | ({32{use_b_f1}} & f1_data) |
   ({32{use_b_m}} & m_data) | ({32{use_b_w}} & w_data) |
   ({32{use_b_w1}} & w1_data);
  assign available_a[s]=!wa[s] || hit_fa[s] || hit_f1a[s] || hit_ma[s] || hit_wa[s] || hit_w1a[s];
  assign available_b[s]=!wb[s] || hit_fb[s] || hit_f1b[s] || hit_mb[s] || hit_wb[s] || hit_w1b[s];
  wire h_c_f=sf_c[s] && f_valid;
  wire h_c_f1=sf1_c[s] && f1_valid;
  wire h_c_m=sm_c[s] && m_valid;
  wire h_c_w=sw_c[s] && w_valid;
  wire h_c_w1=sw1_c[s] && w1_valid;
  assign available_c[s]=!wc[s] || h_c_f || h_c_f1 || h_c_m || h_c_w || h_c_w1;
  wire use_c_f=wc[s] && h_c_f;
  wire use_c_f1=wc[s] && !(h_c_f) && h_c_f1;
  wire use_c_m=wc[s] && !(h_c_f || h_c_f1) && h_c_m;
  wire use_c_w=wc[s] && !(h_c_f || h_c_f1 || h_c_m) && h_c_w;
  wire use_c_w1=wc[s] && !(h_c_f || h_c_f1 || h_c_m || h_c_w) && h_c_w1;
  assign selected_c[s]=({32{!wc[s]}} & side[s][135:104]) |
   ({32{use_c_f}} & f_data) |
   ({32{use_c_f1}} & f1_data) |
   ({32{use_c_m}} & m_data) |
   ({32{use_c_w}} & w_data) |
   ({32{use_c_w1}} & w1_data);
  wire h_d_f=sf_d[s] && f_valid;
  wire h_d_f1=sf1_d[s] && f1_valid;
  wire h_d_m=sm_d[s] && m_valid;
  wire h_d_w=sw_d[s] && w_valid;
  wire h_d_w1=sw1_d[s] && w1_valid;
  assign available_d[s]=!wd[s] || h_d_f || h_d_f1 || h_d_m || h_d_w || h_d_w1;
  wire use_d_f=wd[s] && h_d_f;
  wire use_d_f1=wd[s] && !(h_d_f) && h_d_f1;
  wire use_d_m=wd[s] && !(h_d_f || h_d_f1) && h_d_m;
  wire use_d_w=wd[s] && !(h_d_f || h_d_f1 || h_d_m) && h_d_w;
  wire use_d_w1=wd[s] && !(h_d_f || h_d_f1 || h_d_m || h_d_w) && h_d_w1;
  assign selected_d[s]=({32{!wd[s]}} & side[s][103:72]) |
   ({32{use_d_f}} & f_data) |
   ({32{use_d_f1}} & f1_data) |
   ({32{use_d_m}} & m_data) |
   ({32{use_d_w}} & w_data) |
   ({32{use_d_w1}} & w1_data);
 end endgenerate
 wire[31:0] a=selected_va[rd],b=selected_vb[rd];
 assign out_valid=count!=0 && available_a[rd] && available_b[rd] && available_c[rd] && available_d[rd];
 assign occupied=count!=0;assign in_ready=count!=2;assign out_tag=token[rd];
 assign out_packet={payload[rd][203:136],a,b,payload[rd][71:0]};
 wire push=in_valid && in_ready,pop=out_valid && out_ready;
 // Free physical slots may sample the next operand values before issue.
 // No valid/token/wait state changes before push. Count/rd are registered,
 // so a late decoder/issue signal no longer drives the wide value FF CE.
 wire[1:0] free_slot={count==0 || (count==1 && !rd),count==0 || (count==1 && rd)};
 wire[31:0] incoming_a=(wait_a && f_valid && tag_a==f_tag) ? f_data : (wait_a && f1_valid && tag_a==f1_tag) ? f1_data : (wait_a && m_valid && tag_a==m_tag) ? m_data : (wait_a && w_valid && tag_a==w_tag) ? w_data : (wait_a && w1_valid && tag_a==w1_tag) ? w1_data : in_packet[135:104];
 wire[31:0] incoming_b=(wait_b && f_valid && tag_b==f_tag) ? f_data : (wait_b && f1_valid && tag_b==f1_tag) ? f1_data : (wait_b && m_valid && tag_b==m_tag) ? m_data : (wait_b && w_valid && tag_b==w_tag) ? w_data : (wait_b && w1_valid && tag_b==w1_tag) ? w1_data : in_packet[103:72];
 wire[31:0] incoming_c=(wait_c && f_valid && tag_c==f_tag) ? f_data : (wait_c && f1_valid && tag_c==f1_tag) ? f1_data : (wait_c && m_valid && tag_c==m_tag) ? m_data : (wait_c && w_valid && tag_c==w_tag) ? w_data : (wait_c && w1_valid && tag_c==w1_tag) ? w1_data : in_side[135:104];
 wire[31:0] incoming_d=(wait_d && f_valid && tag_d==f_tag) ? f_data : (wait_d && f1_valid && tag_d==f1_tag) ? f1_data : (wait_d && m_valid && tag_d==m_tag) ? m_data : (wait_d && w_valid && tag_d==w_tag) ? w_data : (wait_d && w1_valid && tag_d==w1_tag) ? w1_data : in_side[103:72];
 integer i;
 always @(posedge clk) begin
  for(i=0;i<2;i=i+1) begin
   if(free_slot[i]) begin
    // Only unoccupied physical slots sample metadata. Push continues to
    // control count/wr/wait state, never widening into packet storage CE.
    side[i][223:136]<=in_side[223:136];side[i][71:0]<=in_side[71:0];
    payload[i]<=in_packet;controls[i]<=in_control;token[i]<=in_tag;
    dep_a[i]<=tag_a;dep_b[i]<=tag_b;dep_c[i]<=tag_c;dep_d[i]<=tag_d;
    predictions[i]<=in_prediction;
    va[i]<=incoming_a;vb[i]<=incoming_b;
    side[i][135:104]<=incoming_c;side[i][103:72]<=incoming_d;
   end
   sf_a[i]<=((push && wr==i[0]) ? tag_a : dep_a[i])=={next_f_tag,1'b0};
   sf1_a[i]<=((push && wr==i[0]) ? tag_a : dep_a[i])=={next_f_tag,1'b1};
   sm_a[i]<=((push && wr==i[0]) ? tag_a : dep_a[i])==next_m_tag;
   sw_a[i]<=((push && wr==i[0]) ? tag_a : dep_a[i])=={next_w_tag,1'b0};
   sw1_a[i]<=((push && wr==i[0]) ? tag_a : dep_a[i])=={next_w_tag,1'b1};
   sf_b[i]<=((push && wr==i[0]) ? tag_b : dep_b[i])=={next_f_tag,1'b0};
   sf1_b[i]<=((push && wr==i[0]) ? tag_b : dep_b[i])=={next_f_tag,1'b1};
   sm_b[i]<=((push && wr==i[0]) ? tag_b : dep_b[i])==next_m_tag;
   sw_b[i]<=((push && wr==i[0]) ? tag_b : dep_b[i])=={next_w_tag,1'b0};
   sw1_b[i]<=((push && wr==i[0]) ? tag_b : dep_b[i])=={next_w_tag,1'b1};
   sf_c[i]<=((push && wr==i[0]) ? tag_c : dep_c[i])=={next_f_tag,1'b0};
   sf1_c[i]<=((push && wr==i[0]) ? tag_c : dep_c[i])=={next_f_tag,1'b1};
   sm_c[i]<=((push && wr==i[0]) ? tag_c : dep_c[i])==next_m_tag;
   sw_c[i]<=((push && wr==i[0]) ? tag_c : dep_c[i])=={next_w_tag,1'b0};
   sw1_c[i]<=((push && wr==i[0]) ? tag_c : dep_c[i])=={next_w_tag,1'b1};
   sf_d[i]<=((push && wr==i[0]) ? tag_d : dep_d[i])=={next_f_tag,1'b0};
   sf1_d[i]<=((push && wr==i[0]) ? tag_d : dep_d[i])=={next_f_tag,1'b1};
   sm_d[i]<=((push && wr==i[0]) ? tag_d : dep_d[i])==next_m_tag;
   sw_d[i]<=((push && wr==i[0]) ? tag_d : dep_d[i])=={next_w_tag,1'b0};
   sw1_d[i]<=((push && wr==i[0]) ? tag_d : dep_d[i])=={next_w_tag,1'b1};

   if(wa[i] && available_a[i]) begin if(!free_slot[i]) va[i]<=selected_va[i];wa[i]<=0;end
   if(wb[i] && available_b[i]) begin if(!free_slot[i]) vb[i]<=selected_vb[i];wb[i]<=0;end
   if(wc[i] && available_c[i]) begin if(!free_slot[i]) side[i][135:104]<=selected_c[i];wc[i]<=0;end
   if(wd[i] && available_d[i]) begin if(!free_slot[i]) side[i][103:72]<=selected_d[i];wd[i]<=0;end
  end
  if(push) begin
   wc[wr]<=wait_c;wd[wr]<=wait_d;
   if(wait_c && f_valid && tag_c==f_tag) begin wc[wr]<=0;end
   else if(wait_c && f1_valid && tag_c==f1_tag) begin wc[wr]<=0;end
   else if(wait_c && m_valid && tag_c==m_tag) begin wc[wr]<=0;end
   else if(wait_c && w_valid && tag_c==w_tag) begin wc[wr]<=0;end
   else if(wait_c && w1_valid && tag_c==w1_tag) begin wc[wr]<=0;end
   if(wait_d && f_valid && tag_d==f_tag) begin wd[wr]<=0;end
   else if(wait_d && f1_valid && tag_d==f1_tag) begin wd[wr]<=0;end
   else if(wait_d && m_valid && tag_d==m_tag) begin wd[wr]<=0;end
   else if(wait_d && w_valid && tag_d==w_tag) begin wd[wr]<=0;end
   else if(wait_d && w1_valid && tag_d==w1_tag) begin wd[wr]<=0;end
   
   wa[wr]<=wait_a;wb[wr]<=wait_b;
   if(wait_a && f_valid && tag_a==f_tag) begin wa[wr]<=0;end
   else if(wait_a && f1_valid && tag_a==f1_tag) begin wa[wr]<=0;end
   else if(wait_a && m_valid && tag_a==m_tag) begin wa[wr]<=0;end
   else if(wait_a && w_valid && tag_a==w_tag) begin wa[wr]<=0;end
   else if(wait_a && w1_valid && tag_a==w1_tag) begin wa[wr]<=0;end
   if(wait_b && f_valid && tag_b==f_tag) begin wb[wr]<=0;end
   else if(wait_b && f1_valid && tag_b==f1_tag) begin wb[wr]<=0;end
   else if(wait_b && m_valid && tag_b==m_tag) begin wb[wr]<=0;end
   else if(wait_b && w_valid && tag_b==w_tag) begin wb[wr]<=0;end
   else if(wait_b && w1_valid && tag_b==w1_tag) begin wb[wr]<=0;end
  end
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin rd<=0;wr<=0;count<=0;end
  else if(clear) begin rd<=0;wr<=0;count<=0;end
  else begin
   if(push) wr<=!wr;if(pop) rd<=!rd;
   case({push,pop}) 2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:;endcase
  end
 end
endmodule
