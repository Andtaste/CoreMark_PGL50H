`timescale 1ns/1ps
module core_tb;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[31:0] ticks=0;
 wire iv,ir,iv_rsp,iready,dv,dr,dv_rsp,dready,dwrite;
 wire[31:0] ia,da,dw,idata,ddata;wire[3:0] mask;
 wire ie,de,tv,tt;wire[31:0] tp,ti,td,tc;wire[4:0] tr;
 reg irq_soft=0,irq_timer=0,irq_ext=0;
 nc_core dut(.clk(clk),.rst_n(rst_n),.irq_soft(irq_soft),.irq_timer(irq_timer),.irq_ext(irq_ext),
  .i_req_valid(iv),.i_req_ready(ir),.i_addr(ia),.i_rsp_valid(iv_rsp),.i_rsp_ready(iready),.i_data(idata),.i_error(ie),
  .d_req_valid(dv),.d_req_ready(dr),.d_addr(da),.d_wdata(dw),.d_mask(mask),.d_write(dwrite),
  .d_rsp_valid(dv_rsp),.d_rsp_ready(dready),.d_rdata(ddata),.d_error(de),
  .trace_valid(tv),.trace_trap(tt),.trace_pc(tp),.trace_insn(ti),.trace_data(td),.trace_cause(tc),.trace_rd(tr));
 reg[31:0] mem[0:24575];
 reg[31:0] lfsr=32'h37a91b21;
 reg ipending=0,dpending=0,irsp=0,drsp=0;
 reg[31:0] iq=0,dq=0;reg ierr=0,derr=0;
 integer idelay=0,ddelay=0,i,fd,seed=1,limit=2000000,finish_count=0;
 integer retired=0,traps=0,overlap=0;
`ifdef MUL_PIPE_TEST
 integer mul_accepts=0,mul_consumes=0,mul_overlap=0,mul_mem_overlap=0,mul_cancels=0,mul_streak=0,mul_max_streak=0;
 always @(posedge clk) if(rst_n) begin
  if(dut.wb_valid && (!dut.live[dut.w_tag] || dut.w_tag!=dut.head)) $fatal(1,"MUL retirement order/token mismatch");
  if(dut.mul_accept) begin
   mul_accepts=mul_accepts+1;mul_streak=mul_streak+1;
   if(mul_streak>mul_max_streak) mul_max_streak=mul_streak;
   if(dut.multiply.available[dut.ex_tag]) $fatal(1,"MUL token reused before result consumed");
   if(dut.memory.state) mul_mem_overlap=mul_mem_overlap+1;
  end else mul_streak=0;
  if(dut.ex_fire && !dut.ex_multiply && dut.mul_busy) mul_overlap=mul_overlap+1;
  if(dut.mul_consume) begin
   mul_consumes=mul_consumes+1;
   if(!dut.mul_query_ready) $fatal(1,"MUL consumed before result ready");
  end
  if(dut.do_trap && dut.mul_busy) mul_cancels=mul_cancels+1;
  if(dut.m_valid && !dut.live[dut.m_tag]) $fatal(1,"MUL completion for dead token");
 end
`endif
 reg ihold=0,dhold=0;reg[31:0] lastia;reg[68:0] lastd;
 reg[1023:0] image,tracefile;
 function integer index;
 input[31:0] addr;
 begin index=addr<65536 ? addr>>2 : addr>=32'h10000000 && addr<32'h10008000 ? 16384+((addr-32'h10000000)>>2) : -1;end
 endfunction
 assign ir=!ipending && !irsp && lfsr[0];
 assign dr=!dpending && !drsp && lfsr[3];
 assign iv_rsp=irsp;assign dv_rsp=drsp;assign idata=iq;assign ddata=dq;assign ie=ierr;assign de=derr;
 initial begin
  for(i=0;i<24576;i=i+1) mem[i]=0;
  if(!$value$plusargs("image=%s",image)) $fatal(1,"missing image");
  if(!$value$plusargs("trace=%s",tracefile)) tracefile="trace.txt";
  if($value$plusargs("seed=%d",seed)) lfsr=seed;
  if($value$plusargs("limit=%d",limit)) begin end
  $readmemh(image,mem,0,16383);fd=$fopen(tracefile,"w");
  repeat(5) @(negedge clk);rst_n=1;
 end
 always @(posedge clk) if(rst_n) begin
  ticks<=ticks+1;lfsr<={lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};
  if(ticks>limit) $fatal(1,"TIMEOUT pc=%h inflight=%d",tp,dut.inflight);
  if(dut.ex_valid && dut.memory.state!=0) overlap<=overlap+1;
  if(ihold && (!iv || ia!==lastia)) $fatal(1,"IF request changed under backpressure");
  if(dhold && (!dv || {dwrite,mask,dw,da}!==lastd)) $fatal(1,"D request changed under backpressure");
  ihold<=iv && !ir;lastia<=ia;dhold<=dv && !dr;lastd<={dwrite,mask,dw,da};
  if(iv && ir) begin
   ipending<=1;idelay<=1+lfsr[6:4];ierr<=index(ia)<0 || |ia[1:0];
   iq<=index(ia)<0 ? 0 : mem[index(ia)];
  end
  if(ipending) begin if(idelay==0) begin ipending<=0;irsp<=1;end else idelay<=idelay-1;end
  if(irsp && iready) irsp<=0;
  if(dv && dr) begin
   dpending<=1;ddelay<=1+lfsr[10:8];dq<=0;derr<=0;
`ifdef MUL_PIPE_TEST
   ddelay<=48+lfsr[10:8];
`endif
   if(index(da)>=0) begin
    dq<=mem[index(da)];
    if(dwrite) for(i=0;i<4;i=i+1) if(mask[i]) mem[index(da)][8*i+:8]<=dw[8*i+:8];
   end else if(da==32'h20003000 && dwrite) begin
    if(dw!=1) $fatal(1,"SOFTWARE_FAIL %h pc=%h",dw,tp);
    finish_count<=20;
`ifdef MUL_PIPE_TEST
    finish_count<=96;
`endif
   end else if(da==32'h20004000 && dwrite) begin
    irq_soft<=dw[0];irq_timer<=dw[1];irq_ext<=dw[2];
   end else derr<=1;
  end
  if(dpending) begin if(ddelay==0) begin dpending<=0;drsp<=1;end else ddelay<=ddelay-1;end
  if(drsp && dready) drsp<=0;
  if(tv) begin
   $fdisplay(fd,"%08x %08x %d %08x %d %08x",tp,ti,tr,td,tt,tc);
   if(tt) traps<=traps+1;else retired<=retired+1;
  end
  if(finish_count!=0) begin
   finish_count<=finish_count-1;
   if(finish_count==1) begin
    $display("PASS cycles=%d retired=%d traps=%d overlap=%d",ticks,retired,traps,overlap);
`ifdef MUL_PIPE_TEST
    $display("MUL_CORE accepts=%0d consumes=%0d overlap=%0d mem_overlap=%0d trap_cancels=%0d max_accept_streak=%0d",
     mul_accepts,mul_consumes,mul_overlap,mul_mem_overlap,mul_cancels,mul_max_streak);
`endif
    $fclose(fd);$finish;
   end
  end
 end
endmodule
