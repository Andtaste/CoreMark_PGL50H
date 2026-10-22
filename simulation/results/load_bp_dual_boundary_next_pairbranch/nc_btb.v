// One PC[2] bank of the same 64-entry BTB: 32 entries, full PC[31:8] tag. Each entry
// has one resolved local-history bit and two saturating two-bit counters.
// History is updated only by registered, resolved training, never by an
// unregistered EX control or speculative IF event. Only valid bits reset.
module nc_btb_bank(input wire clk,rst_n,flush,
 input wire[31:0] lookup_pc,output wire[31:0] prediction,
 input wire update_valid,update_branch,update_conditional,update_taken,
 input wire[31:0] update_pc,update_target);
 reg[31:0] valid;
 reg[23:0] tags[0:31] /* synthesis syn_ramstyle="lut_ram" */;
 reg[29:0] targets[0:31] /* synthesis syn_ramstyle="lut_ram" */;
 reg conditional[0:31] /* synthesis syn_ramstyle="lut_ram" */;
 // {last resolved outcome, counter after taken, counter after not-taken}.
 reg[4:0] directions[0:31] /* synthesis syn_ramstyle="lut_ram" */;
 wire[4:0] r=lookup_pc[7:3],w=update_pc[7:3];
 wire hit=valid[r] && tags[r]==lookup_pc[31:8];
 wire[4:0] read_direction=directions[r];
 wire predicted_direction=read_direction[4] ? read_direction[3] : read_direction[1];
 wire predict_taken=hit && (!conditional[r] || predicted_direction);
 // [31]=hit, [30]=taken, [29:0]=word target; sequential PC is implicit.
 assign prediction={hit,predict_taken,targets[r]};
 wire same_entry=valid[w] && tags[w]==update_pc[31:8];
 wire[4:0] old_direction=directions[w];
 wire[1:0] prior=old_direction[4] ? old_direction[3:2] : old_direction[1:0];
 wire[1:0] trained=update_taken ? (prior==3 ? 2'd3 : prior+2'd1) :
                                              (prior==0 ? 2'd0 : prior-2'd1);
 always @(posedge clk) if(update_valid && update_branch && !flush) begin
  tags[w]<=update_pc[31:8];targets[w]<=update_target[31:2];conditional[w]<=update_conditional;
  // Allocation initializes both contexts, avoiding reads of stale history
  // belonging to a colliding PC. Training uses the last resolved context;
  // lookup and training are intentionally not joined by a write-through mux.
  directions[w]<=!update_conditional ? 5'b01111 : !same_entry ?
    {update_taken,{2{update_taken ? 2'b10 : 2'b01}}} :
    {update_taken,(old_direction[4] ? trained : old_direction[3:2]),
                  (old_direction[4] ? old_direction[1:0] : trained)};
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) valid<=0;
  else if(flush) valid<=0;
  else if(update_valid) begin
   if(update_branch) valid[w]<=1;
   else if(same_entry) valid[w]<=0;
  end
 end
endmodule
