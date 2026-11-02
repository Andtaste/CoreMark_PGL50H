// Dedicated IF=A, LSU=B Pango TDP RAM ports: no IF/LSU port crossbar.
// Full range decode prevents RAM address aliases. Responses retain bank/error
// ownership. MMIO is authorized only by an accepted MEM request.
module nc_local_bus #(parameter CLOCK_HZ=75000000)(input wire clk,rst_n,
 input wire iv,output wire ir,input wire[31:0] ia,output wire iov,input wire ior,
 output wire[63:0] idata,output wire ierr,
 input wire dv,output wire dr,input wire[31:0] da,dw,wa,input wire[3:0] dm,input wire dwrite,
 output wire dov,input wire dor,output wire[31:0] ddata,output wire[63:0] dline,output wire derr,
 output wire uart_tx,output wire timer_irq,output wire[1:0] gpio_out,
 output reg[31:0] tohost);
 wire ib0=ia<32'h00010000,ib1=ia>=32'h10000000 && ia<32'h10008000;
 wire db0=da<32'h00010000,db1=da>=32'h10000000 && da<32'h10008000;
 reg ipending,ibank,ierror;reg dpending,dbank,dis_ram,derror,dhalf;reg[31:0] mmio_data;
 wire[63:0] iq0,iq1,dq0,dq1;

 wire uart_ready;wire uart_addr=wa==32'h20000000;
 wire uart_send=dv && dr && dwrite && uart_addr && dm[0];
 nc_uart #(.CLOCK_HZ(CLOCK_HZ)) uart(.clk(clk),.rst_n(rst_n),.send(uart_send),.data(dw[7:0]),.ready(uart_ready),.tx(uart_tx));
 assign dr=rst_n && (!dpending || dor) && !(dwrite && uart_addr && !uart_ready);
 wire da_fire=dv && dr;
 // Avoid undefined cross-port read-during-write on the same physical word.
 // FENCE.I discards previously fetched words for self-modifying code.
 // dwrite is a published-write qualifier: it implies dv. Its address is
 // registered in MEM, so EX load/branch data cannot enter IF collision control.
 wire wb0=wa<32'h00010000,wb1=wa>=32'h10000000 && wa<32'h10008000;
 wire collision=dr && dwrite && ((ib0 && wb0)||(ib1 && wb1)) && ia[15:3]==wa[15:3];
 assign ir=rst_n && (!ipending || ior) && !collision;
 wire ia_fire=iv && ir;
 assign iov=ipending;assign ierr=ierror;assign idata=ibank ? iq1 : iq0;
 assign dov=dpending;assign derr=derror;assign dline=dbank ? dq1 : dq0;assign ddata=dis_ram ? (dhalf ? dline[63:32] : dline[31:0]) : mmio_data;
 reg[63:0] mtime,mtimecmp;reg[1:0] gpio;
 assign timer_irq=mtime>=mtimecmp;assign gpio_out=gpio;
 reg mmio_known;reg[31:0] read_mmio;
 always @* begin
  mmio_known=1;read_mmio=0;
  case(da)
   32'h20000000:read_mmio=0;
   32'h20000004:read_mmio={31'b0,uart_ready};
   32'h20001000:read_mmio=mtime[31:0];32'h20001004:read_mmio=mtime[63:32];
   32'h20001008:read_mmio=mtimecmp[31:0];32'h2000100c:read_mmio=mtimecmp[63:32];
   32'h20002000:read_mmio={30'b0,gpio};32'h20003000:read_mmio=tohost;
   default:mmio_known=0;
  endcase
 end
 integer j;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   ipending<=0;ibank<=0;ierror<=0;dpending<=0;dbank<=0;dhalf<=0;dis_ram<=0;derror<=0;mmio_data<=0;
   mtime<=0;mtimecmp<=64'hffffffffffffffff;gpio<=0;tohost<=0;
  end else begin
   mtime<=mtime+1'b1;
   if(ia_fire) begin ipending<=1;ibank<=ib1;ierror<=!(ib0 || ib1) || |ia[1:0];end
   else if(iov && ior) ipending<=0;
   if(da_fire) begin
    dpending<=1;dbank<=db1;dhalf<=da[2];dis_ram<=db0 || db1;derror<=!(db0 || db1 || mmio_known);mmio_data<=read_mmio;
   end else if(dov && dor) dpending<=0;
   // dwrite is published only for a valid held MEM store. Do not put the
   // early-load valid/range cone in series with these write side effects.
   if(dwrite && dr) begin
     for(j=0;j<4;j=j+1) if(dm[j]) case(wa)
      32'h20001008:mtimecmp[j*8+:8]<=dw[j*8+:8];
      32'h2000100c:mtimecmp[32+j*8+:8]<=dw[j*8+:8];
      32'h20003000:tohost[j*8+:8]<=dw[j*8+:8];
      default:;
     endcase
     if(wa==32'h20002000 && dm[0]) gpio<=dw[1:0];
   end
  end
 end
 ram1_tdp ram_code(.a_clk(clk),.a_rst(!rst_n),.a_clk_en(ia_fire && ib0 && !ia[1] && !ia[0]),
  .a_addr(ia[15:3]),.a_wr_data(64'b0),.a_wr_en(1'b0),.a_wr_byte_en(8'b0),.a_rd_data(iq0),
  .b_clk(clk),.b_rst(!rst_n),.b_clk_en(da_fire && db0),.b_addr(da[15:3]),
  .b_wr_data({dw,dw}),.b_wr_en(dwrite),.b_wr_byte_en(!dwrite ? 8'hff : wa[2] ? {dm,4'b0} : {4'b0,dm}),.b_rd_data(dq0));

 ram2_tdp ram_data(.a_clk(clk),.a_rst(!rst_n),.a_clk_en(ia_fire && ib1 && !ia[1] && !ia[0]),
  .a_addr(ia[14:3]),.a_wr_data(64'b0),.a_wr_en(1'b0),.a_wr_byte_en(8'b0),.a_rd_data(iq1),
  .b_clk(clk),.b_rst(!rst_n),.b_clk_en(da_fire && db1),.b_addr(da[14:3]),
  .b_wr_data({dw,dw}),.b_wr_en(dwrite),.b_wr_byte_en(!dwrite ? 8'hff : wa[2] ? {dm,4'b0} : {4'b0,dm}),.b_rd_data(dq1));

endmodule
