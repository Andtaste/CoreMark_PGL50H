// One PC[2] bank of the same 64-entry BTB: 32 entries, full PC[31:8] tag. Each entry
// has one resolved local-history bit and two saturating two-bit counters.
// History is updated only by registered, resolved training, never by an
// unregistered EX control or speculative IF event. Only valid bits reset.
module nc_btb_way #(parameter COMPACT_LOCAL=0)(input wire clk,rst_n,flush,
 input wire[31:0] lookup_pc,output wire[31:0] prediction,
 input wire update_valid,update_branch,update_conditional,update_taken,
 input wire[31:0] update_pc,update_target,output wire update_hit,update_slot_valid);
 function local_address(input[31:0] x);
  local_address=x[1:0]==0 && (x[31:16]==0 || x[31:15]==17'h2000);
 endfunction
 localparam TAG_BITS=COMPACT_LOCAL ? 9 : 24,TARGET_BITS=COMPACT_LOCAL ? 15 : 30;
 wire[TAG_BITS-1:0] read_tag=COMPACT_LOCAL ? {lookup_pc[28],lookup_pc[15:8]} : lookup_pc[31:8];
 wire[TAG_BITS-1:0] write_tag=COMPACT_LOCAL ? {update_pc[28],update_pc[15:8]} : update_pc[31:8];
 wire[TARGET_BITS-1:0] write_target=COMPACT_LOCAL ? {update_target[28],update_target[15:2]} : update_target[31:2];
 reg[31:0] valid;
 reg[TAG_BITS-1:0] tags[0:31] /* synthesis syn_ramstyle="lut_ram" */;
 reg[TARGET_BITS-1:0] targets[0:31] /* synthesis syn_ramstyle="lut_ram" */;
 reg conditional[0:31] /* synthesis syn_ramstyle="lut_ram" */;
 // {last resolved outcome, counter after taken, counter after not-taken}.
 reg[4:0] directions[0:31] /* synthesis syn_ramstyle="lut_ram" */;
 wire[4:0] r=lookup_pc[7:3]^lookup_pc[14:10],w=update_pc[7:3]^update_pc[14:10];
 wire hit=valid[r] && tags[r]==read_tag && (!COMPACT_LOCAL || local_address(lookup_pc));
 wire[4:0] read_direction=directions[r];
 wire predicted_direction=read_direction[4] ? read_direction[3] : read_direction[1];
 wire predict_taken=hit && (!conditional[r] || predicted_direction);
 // [31]=hit, [30]=taken, [29:0]=word target; sequential PC is implicit.
 wire[29:0] read_target=COMPACT_LOCAL ? {3'b0,targets[r][14],12'b0,targets[r][13:0]} : targets[r];
 assign prediction={hit,predict_taken,read_target};
 wire same_entry=valid[w] && tags[w]==write_tag;
 assign update_hit=same_entry;assign update_slot_valid=valid[w];
 wire[4:0] old_direction=directions[w];
 wire[1:0] prior=old_direction[4] ? old_direction[3:2] : old_direction[1:0];
 wire[1:0] trained=update_taken ? (prior==3 ? 2'd3 : prior+2'd1) :
                                              (prior==0 ? 2'd0 : prior-2'd1);
 always @(posedge clk) if(update_valid && update_branch && !flush) begin
  tags[w]<=write_tag;targets[w]<=write_target;conditional[w]<=update_conditional;
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

module nc_btb_bank #(parameter COMPACT_LOCAL=0)(input wire clk,rst_n,flush,
 input wire[31:0] lookup_pc,output wire[31:0] prediction,
 input wire update_valid,update_branch,update_conditional,update_taken,
 input wire[31:0] update_pc,update_target);
 function local_address(input[31:0] x);
  local_address=x[1:0]==0 && (x[31:16]==0 || x[31:15]==17'h2000);
 endfunction
 // Unsupported PCs miss. Unsupported branch targets invalidate an old hit,
 // rather than allocating a truncated target. Defaults retain full-PC behavior.
 wire train_valid=update_valid && (!COMPACT_LOCAL || local_address(update_pc));
 wire train_branch=update_branch && (!COMPACT_LOCAL || local_address(update_target));
 localparam WAYS=4;
 wire[WAYS-1:0] hits,slots;wire[31:0] preds[0:WAYS-1];
 reg[1:0] replacement[0:31];wire[4:0] w=update_pc[7:3]^update_pc[14:10];
 reg[1:0] chosen;integer j;reg found;
 always @* begin
 chosen=replacement[w];found=0;
 for(j=0;j<WAYS;j=j+1) if(!found && hits[j]) begin chosen=j;found=1;end
 if(!found) for(j=0;j<WAYS;j=j+1) if(!found && !slots[j]) begin chosen=j;found=1;end
 end
 always @(posedge clk) if(train_valid && train_branch && !flush && !(|hits)) replacement[w]<=chosen==WAYS-1 ? 2'd0 : chosen+2'd1;
 genvar k;
 generate for(k=0;k<WAYS;k=k+1) begin:ways
 nc_btb_way #(.COMPACT_LOCAL(COMPACT_LOCAL)) entry(.clk(clk),.rst_n(rst_n),.flush(flush),.lookup_pc(lookup_pc),.prediction(preds[k]),
 .update_valid(train_valid && (train_branch ? chosen==k : hits[k])),.update_branch(train_branch),.update_conditional(update_conditional),.update_taken(update_taken),.update_pc(update_pc),.update_target(update_target),.update_hit(hits[k]),.update_slot_valid(slots[k]));
 end endgenerate
 reg[31:0] selected;integer n;
 always @* begin selected=0;for(n=0;n<WAYS;n=n+1) selected=selected|({32{preds[n][31]}} & preds[n]);end
 assign prediction=selected;
endmodule
