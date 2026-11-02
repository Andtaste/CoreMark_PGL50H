// A response retains its local/DDR owner until accepted. No detached DDR stores.
module nc_bus_router #(parameter CLOCK_HZ=80000000)(
 input wire clk,rst_n,input wire iv,output wire ir,input wire[31:0] ia,
 output wire iov,input wire ior,output wire[63:0] idata,output wire ierr,
 input wire dv,output wire dr,input wire[31:0] da,dw,wa,input wire[3:0] dm,input wire dwrite,
 output wire dov,input wire dor,output wire[31:0] ddata,output wire[63:0] dline,output wire derr,
 input wire uart_rx,output wire uart_tx,output wire timer_irq,output wire[1:0] gpio_out,output wire[31:0] tohost,
 input wire ddr_ready,input wire[31:0] ddr_reads,ddr_writes,ddr_hits,ddr_wait,
 output wire ext_valid,input wire ext_ready,output wire ext_write,ext_clear,
 output wire[23:0] ext_address,output wire[31:0] ext_data,output wire[3:0] ext_mask,
 input wire ext_rsp_valid,output wire ext_rsp_ready,input wire[63:0] ext_rsp_line
);
 reg occupied,remote_owner,half;
 wire remote_memory=da[31:24]==8'h40;
 wire clear_memory=da==32'h20004004 && dwrite && dm[0] && dw[0];
 wire remote=remote_memory || clear_memory;
 wire local_ready,local_valid,local_error;wire[31:0] local_data;wire[63:0] local_line;
 wire credit=!occupied || (dov && dor);
 assign dr=rst_n && credit && (remote ? ext_ready : local_ready);
 assign ext_valid=dv && rst_n && credit && remote;
 assign ext_write=dwrite;assign ext_clear=clear_memory;assign ext_address=da[23:0];assign ext_data=dw;assign ext_mask=dm;
 assign ext_rsp_ready=occupied && remote_owner && dor;
 assign dov=occupied && (remote_owner ? ext_rsp_valid : local_valid);
 assign derr=occupied && !remote_owner && local_error;
 assign dline=remote_owner ? ext_rsp_line : local_line;
 assign ddata=remote_owner ? (half ? ext_rsp_line[63:32] : ext_rsp_line[31:0]) : local_data;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin occupied<=0;remote_owner<=0;half<=0;end
  else if(dv && dr)begin occupied<=1;remote_owner<=remote;half<=da[2];end
  else if(dov && dor)occupied<=0;
 end
 nc_local_bus #(.CLOCK_HZ(CLOCK_HZ)) local_bus(.clk(clk),.rst_n(rst_n),.iv(iv),.ir(ir),.ia(ia),.iov(iov),.ior(ior),.idata(idata),.ierr(ierr),
 .dv(dv && credit && !remote),.dr(local_ready),.da(da),.dw(dw),.wa(wa),.dm(dm),.dwrite(dwrite && credit && !remote),
 .dov(local_valid),.dor(dor && occupied && !remote_owner),.ddata(local_data),.dline(local_line),.derr(local_error),
 .uart_rx(uart_rx),.uart_tx(uart_tx),.timer_irq(timer_irq),.gpio_out(gpio_out),.tohost(tohost),
 .ddr_ready(ddr_ready),.ddr_reads(ddr_reads),.ddr_writes(ddr_writes),.ddr_hits(ddr_hits),.ddr_wait(ddr_wait));
endmodule
