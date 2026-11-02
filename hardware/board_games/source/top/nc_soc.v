module nc_soc #(parameter CLOCK_HZ=80000000)(input wire clk,rst_n,uart_rx,input wire irq_soft,irq_ext,
 output wire uart_tx,output wire[1:0] gpio_out,output wire[31:0] tohost,
 input wire ddr_ready,input wire[31:0] ddr_reads,ddr_writes,ddr_hits,ddr_wait,
 output wire ext_valid,input wire ext_ready,output wire ext_write,ext_clear,
 output wire[23:0] ext_address,output wire[31:0] ext_data,output wire[3:0] ext_mask,
 input wire ext_rsp_valid,output wire ext_rsp_ready,input wire[63:0] ext_rsp_line);
 wire iv,ir,iov,ior,ie,dv,dr,dov,dor,de,dwrite,timer_irq;
 wire[63:0] idata,dline;wire[31:0] ia,da,dw,ddata,wa;wire[3:0] dm;
 // This local bus acknowledges every accepted in-range BRAM write without
 // late errors. Standalone nc_core keeps posted completion disabled.
 nc_core #(.POST_LOCAL_STORES(1),.BULK_READ_FILL(1),.LOCAL_DATA_BITS(17),.L0_INDEX_BITS(9)) cpu(.clk(clk),.rst_n(rst_n),.irq_soft(irq_soft),.irq_timer(timer_irq),.irq_ext(irq_ext),
  .i_req_valid(iv),.i_req_ready(ir),.i_addr(ia),.i_rsp_valid(iov),.i_rsp_ready(ior),.i_data(idata),.i_error(ie),
  .d_write_addr(wa),.d_req_valid(dv),.d_req_ready(dr),.d_addr(da),.d_wdata(dw),.d_mask(dm),.d_write(dwrite),
  .d_rsp_valid(dov),.d_rsp_ready(dor),.d_rdata(ddata),.d_line_data(dline),.d_error(de),
  .trace_valid(),.trace_trap(),.trace_pc(),.trace_insn(),.trace_data(),.trace_cause(),.trace_rd());
 nc_bus_router #(.CLOCK_HZ(CLOCK_HZ)) bus(.clk(clk),.rst_n(rst_n),.iv(iv),.ir(ir),.ia(ia),.iov(iov),.ior(ior),.idata(idata),.ierr(ie),
  .dv(dv),.dr(dr),.wa(wa),.da(da),.dw(dw),.dm(dm),.dwrite(dwrite),.dov(dov),.dor(dor),.ddata(ddata),.dline(dline),.derr(de),
  .uart_rx(uart_rx),.uart_tx(uart_tx),.timer_irq(timer_irq),.gpio_out(gpio_out),.tohost(tohost),
  .ddr_ready(ddr_ready),.ddr_reads(ddr_reads),.ddr_writes(ddr_writes),.ddr_hits(ddr_hits),.ddr_wait(ddr_wait),
  .ext_valid(ext_valid),.ext_ready(ext_ready),.ext_write(ext_write),.ext_clear(ext_clear),.ext_address(ext_address),.ext_data(ext_data),.ext_mask(ext_mask),
  .ext_rsp_valid(ext_rsp_valid),.ext_rsp_ready(ext_rsp_ready),.ext_rsp_line(ext_rsp_line));
endmodule
