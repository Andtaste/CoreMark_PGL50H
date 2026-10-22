"""Bench-only classify head waits by older producer kind, without modifying RTL."""
def instrument(s,cpu):
 block=r'''
 reg[3:0] wk_main[0:7],wk_side[0:7];
 integer wk_all=0,wk_main_only=0,wk_side_only=0,wk_both=0;
 integer wk_side_load=0,wk_side_mul=0,wk_side_div=0,wk_side_alu=0;
 integer wk_relief_load=0,wk_relief_mul=0,wk_relief_div=0,wk_relief_alu=0;
 integer wk_load_rsp_now=0,wk_load_wb_now=0,wk_base_ready=0;
 reg wk_a,wk_b,wk_c,wk_d;reg[3:0] wk_tag,wk_kind;
 reg wk_l,wk_m,wk_v,wk_r;integer wk_j;
 always @(posedge clk) if(rst_n) begin
  if(CPU.issue) begin wk_main[CPU.tail]<=CPU.id_kind;wk_side[CPU.tail]<=CPU.id_side_kind;end
  if(CPU.csr.stats.control && CPU.csr.stats.control_data[1]) begin
   wk_all=0;wk_main_only=0;wk_side_only=0;wk_both=0;
   wk_side_load=0;wk_side_mul=0;wk_side_div=0;wk_side_alu=0;
   wk_relief_load=0;wk_relief_mul=0;wk_relief_div=0;wk_relief_alu=0;
   wk_load_rsp_now=0;wk_load_wb_now=0;wk_base_ready=0;
  end else if(!CPU.csr.stats.control && CPU.csr.stats.enabled && CPU.ex_occupied) begin
   wk_a=CPU.operands.available_a[CPU.operands.rd];wk_b=CPU.operands.available_b[CPU.operands.rd];
   wk_c=CPU.operands.available_c[CPU.operands.rd];wk_d=CPU.operands.available_d[CPU.operands.rd];
   if(!(wk_a && wk_b && wk_c && wk_d)) begin
    wk_all=wk_all+1;
    if(wk_a && wk_b) wk_side_only=wk_side_only+1;
    else if(wk_c && wk_d) wk_main_only=wk_main_only+1;
    else wk_both=wk_both+1;
   end
   wk_l=0;wk_m=0;wk_v=0;wk_r=0;
   for(wk_j=0;wk_j<2;wk_j=wk_j+1) if(wk_j==0 ? !wk_c : !wk_d) begin
    wk_tag=wk_j==0 ? (CPU.operands.rd ? CPU.operands.dep_c[1] : CPU.operands.dep_c[0]) : (CPU.operands.rd ? CPU.operands.dep_d[1] : CPU.operands.dep_d[0]);
    wk_kind=wk_tag[0] ? wk_side[wk_tag[3:1]] : wk_main[wk_tag[3:1]];
    if(wk_kind==4) begin
     wk_l=1;
     if(CPU.d_rsp_valid && CPU.memory.memory_pending && CPU.memory.tag==wk_tag[3:1]) wk_load_rsp_now=wk_load_rsp_now+1;
     if(CPU.commit && CPU.w_tag==wk_tag[3:1]) wk_load_wb_now=wk_load_wb_now+1;
    end else if(wk_kind==6) begin
     // Side MUL never DIV. Primary operation bit2 distinguishes DIV/REM.
     if(wk_tag[0] || !wk_div[wk_tag[3:1]]) wk_m=1;else wk_v=1;
    end else wk_r=1;
   end
   if(wk_l) wk_side_load=wk_side_load+1;if(wk_m) wk_side_mul=wk_side_mul+1;
   if(wk_v) wk_side_div=wk_side_div+1;if(wk_r) wk_side_alu=wk_side_alu+1;
   if(wk_a && wk_b) begin
    if(wk_l) wk_relief_load=wk_relief_load+1;if(wk_m) wk_relief_mul=wk_relief_mul+1;
    if(wk_v) wk_relief_div=wk_relief_div+1;if(wk_r) wk_relief_alu=wk_relief_alu+1;
   end
  end
 end
 reg[7:0] wk_div;
 always @(posedge clk) if(CPU.issue) wk_div[CPU.tail]<=CPU.id_insn[14];
 always @(negedge clk) if(check_secondary) begin
  if(wk_all!=wk_main_only+wk_side_only+wk_both) $fatal(1,"Wait partition mismatch");
  $display("WAIT_KIND all=%0d main_only=%0d side_only=%0d both=%0d side_load=%0d side_mul=%0d side_div=%0d side_alu=%0d relief_load=%0d relief_mul=%0d relief_div=%0d relief_alu=%0d load_rsp_now_operands=%0d load_wb_now_operands=%0d",wk_all,wk_main_only,wk_side_only,wk_both,wk_side_load,wk_side_mul,wk_side_div,wk_side_alu,wk_relief_load,wk_relief_mul,wk_relief_div,wk_relief_alu,wk_load_rsp_now,wk_load_wb_now);
 end
'''
 return s.replace('endmodule',block.replace('CPU',cpu)+'\nendmodule')
