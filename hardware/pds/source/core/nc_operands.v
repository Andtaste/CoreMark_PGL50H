// Two-entry in-order ID/EX boundary, with tagged operand forwarding.
// Only the head executes. Both slots remember broadcasts during stalls.
module nc_operands #(parameter USE_SPLIT_F0=0,REGISTER_LOAD_ADDRESS=0,EARLY_ADDI_AGU=0)(input wire clk,rst_n,clear,input wire early_addi_valid,
 input wire in_valid,output wire in_ready,input wire[203:0] in_packet,input wire[2:0] in_tag,
 input wire[223:0] in_side,output wire[223:0] out_side,
 input wire[18:0] in_control,output wire[18:0] out_control,
 input wire[31:0] in_prediction,output wire[31:0] out_prediction,
 input wire wait_a,wait_b,input wire[3:0] tag_a,tag_b,
 input wire wait_c,wait_d,input wire[3:0] tag_c,tag_d,
 input wire[2:0] next_f_tag,next_w_tag,input wire[3:0] next_m_tag,
 input wire f_valid,input wire[3:0] f_tag,input wire[31:0] f_data,
 input wire[31:0] f_alu_data,f_cache_data,input wire f_is_cache,
 input wire w_valid,input wire[3:0] w_tag,input wire[31:0] w_data,
 input wire m_valid,input wire[3:0] m_tag,input wire[31:0] m_data,
 output wire out_valid,input wire out_ready,output wire[203:0] out_packet,output wire[2:0] out_tag,
 input wire f1_valid,w1_valid,input wire[3:0] f1_tag,w1_tag,input wire[31:0] f1_data,w1_data,
 output wire occupied,output wire[31:0] out_address,output wire[31:0] load_lookup_address);
 wire f_cache_selected=USE_SPLIT_F0 && f_is_cache;
 wire[31:0] f_alu_value=USE_SPLIT_F0 ? f_alu_data : f_data;
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
 wire[1:0] use_a_f,use_a_f1,use_a_m,use_a_w,use_a_w1;
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
  assign use_a_f[s]=wa[s] && hit_fa[s];
  assign use_a_f1[s]=wa[s] && !hit_fa[s] && hit_f1a[s];
  assign use_a_m[s]=wa[s] && !(hit_fa[s] || hit_f1a[s]) && hit_ma[s];
  assign use_a_w[s]=wa[s] && !(hit_fa[s] || hit_f1a[s] || hit_ma[s]) && hit_wa[s];
  assign use_a_w1[s]=wa[s] && !(hit_fa[s] || hit_f1a[s] || hit_ma[s] || hit_wa[s]);
  assign selected_va[s]=({32{!wa[s]}} & va[s]) |
   ({32{use_a_f[s] && !f_cache_selected}} & f_alu_value) | ({32{use_a_f[s] && f_cache_selected}} & f_cache_data) | ({32{use_a_f1[s]}} & f1_data) |
   ({32{use_a_m[s]}} & m_data) | ({32{use_a_w[s]}} & w_data) |
   ({32{use_a_w1[s]}} & w1_data);
  assign hit_f1b[s]=sf1_b[s] && f1_valid;assign hit_w1b[s]=sw1_b[s] && w1_valid;
  // Exclusive priority masks preserve F > F1 > M > W > W1.
  // The W1 fall-through also preserves the old value on unavailable cycles.
  wire use_b_f=wb[s] && hit_fb[s];
  wire use_b_f1=wb[s] && !hit_fb[s] && hit_f1b[s];
  wire use_b_m=wb[s] && !(hit_fb[s] || hit_f1b[s]) && hit_mb[s];
  wire use_b_w=wb[s] && !(hit_fb[s] || hit_f1b[s] || hit_mb[s]) && hit_wb[s];
  wire use_b_w1=wb[s] && !(hit_fb[s] || hit_f1b[s] || hit_mb[s] || hit_wb[s]);
  assign selected_vb[s]=({32{!wb[s]}} & vb[s]) |
   ({32{use_b_f && !f_cache_selected}} & f_alu_value) | ({32{use_b_f && f_cache_selected}} & f_cache_data) | ({32{use_b_f1}} & f1_data) |
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
   ({32{use_c_f && !f_cache_selected}} & f_alu_value) | ({32{use_c_f && f_cache_selected}} & f_cache_data) |
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
   ({32{use_d_f && !f_cache_selected}} & f_alu_value) | ({32{use_d_f && f_cache_selected}} & f_cache_data) |
   ({32{use_d_f1}} & f1_data) |
   ({32{use_d_m}} & m_data) |
   ({32{use_d_w}} & w_data) |
   ({32{use_d_w1}} & w1_data);
 end endgenerate
 wire[31:0] a=selected_va[rd],b=selected_vb[rd];
 // Move the address adders before late broadcast-valid selection. All source
 // values and the immediate have the same cycle ownership as operand A.
 wire[31:0] slot_address[0:1];genvar q;
 generate for(q=0;q<2;q=q+1) begin:address_by_slot
 wire[31:0] imm=payload[q][71:40];
 assign slot_address[q]=({32{!wa[q]}} & (va[q]+imm)) |
({32{use_a_f[q] && !f_cache_selected}} & (f_alu_value+imm)) | ({32{use_a_f[q] && f_cache_selected}} & (f_cache_data+imm)) | ({32{use_a_f1[q]}} & (f1_data+imm)) | ({32{use_a_m[q]}} & (m_data+imm)) | ({32{use_a_w[q]}} & (w_data+imm)) | ({32{use_a_w1[q]}} & (w1_data+imm));
 end endgenerate
 assign out_address=slot_address[rd];
 // REGISTER_ALL_AGU: only address consumers wait for the saved base.
 wire saved_agu_required=(payload[rd][203:200]>=3 && payload[rd][203:200]<=5) ||
                         (controls[rd][0] && controls[rd][15]);
 assign out_valid=count!=0 && (!REGISTER_LOAD_ADDRESS || !saved_agu_required || !wa[rd] || (EARLY_ADDI_AGU && early_address_ready[rd])) && available_a[rd] && available_b[rd] && available_c[rd] && available_d[rd];
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
 reg[31:0] cache_address_q[0:1];
 reg[31:0] early_address_q[0:1];reg[1:0] early_address_ready;
 // Data is captured independently of late producer acceptance. Only the
 // two ownership bits depend on that event; no wide late-valid write CE.
 wire incoming_agu=(in_packet[203:200]>=3 && in_packet[203:200]<=5) || (in_control[0] && in_control[15]);
 genvar ea;generate for(ea=0;ea<2;ea=ea+1) begin:early_addi_address
  wire slot_agu=(payload[ea][203:200]>=3 && payload[ea][203:200]<=5) || (controls[ea][0] && controls[ea][15]);
  always @(posedge clk) early_address_q[ea]<=load_lookup_address +
    (free_slot[ea] ? in_packet[71:40] : payload[ea][71:40]);
  always @(posedge clk or negedge rst_n) begin
   if(!rst_n)early_address_ready[ea]<=0;
   else if(clear)early_address_ready[ea]<=0;
   else early_address_ready[ea]<=EARLY_ADDI_AGU && early_addi_valid &&
    ((push && wr==ea && incoming_agu && wait_a && tag_a=={token[rd],1'b0}) ||
     (!free_slot[ea] && slot_agu && wa[ea] && dep_a[ea]=={token[rd],1'b0}));
  end
 end endgenerate
 assign load_lookup_address=(EARLY_ADDI_AGU && early_address_ready[rd]) ? early_address_q[rd] : cache_address_q[rd];
 wire ca_f=wait_a && f_valid && tag_a==f_tag;
 wire ca_f1=wait_a && !ca_f && f1_valid && tag_a==f1_tag;
 wire ca_m=wait_a && !(ca_f || ca_f1) && m_valid && tag_a==m_tag;
 wire ca_w=wait_a && !(ca_f || ca_f1 || ca_m) && w_valid && tag_a==w_tag;
 wire ca_w1=wait_a && !(ca_f || ca_f1 || ca_m || ca_w) && w1_valid && tag_a==w1_tag;
 wire ca_base=!(ca_f || ca_f1 || ca_m || ca_w || ca_w1);
 wire[31:0] ca_imm=in_packet[71:40];
 wire[31:0] incoming_cache_address=({32{ca_base}} & (in_packet[135:104]+ca_imm)) |
  ({32{ca_f && !f_cache_selected}} & (f_alu_value+ca_imm)) |
  ({32{ca_f && f_cache_selected}} & (f_cache_data+ca_imm)) |
  ({32{ca_f1}} & (f1_data+ca_imm)) | ({32{ca_m}} & (m_data+ca_imm)) |
  ({32{ca_w}} & (w_data+ca_imm)) | ({32{ca_w1}} & (w1_data+ca_imm));
 integer i;
 always @(posedge clk) begin
  for(i=0;i<2;i=i+1) begin
   cache_address_q[i]<=free_slot[i] ? incoming_cache_address : slot_address[i];
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
