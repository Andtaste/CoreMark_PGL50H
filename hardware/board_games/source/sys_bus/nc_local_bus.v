// Dedicated IF=A, LSU=B Pango TDP RAM ports: no IF/LSU port crossbar.
// Full range decode prevents RAM address aliases. Responses retain bank/error
// ownership. MMIO is authorized only by an accepted MEM request.
module nc_local_bus #(parameter CLOCK_HZ=80000000)(input wire clk,rst_n,
 input wire iv,output wire ir,input wire[31:0] ia,output wire iov,input wire ior,
 output wire[63:0] idata,output wire ierr,
 input wire dv,output wire dr,input wire[31:0] da,dw,wa,input wire[3:0] dm,input wire dwrite,
 output wire dov,input wire dor,output wire[31:0] ddata,output wire[63:0] dline,output wire derr,
 input wire uart_rx,output wire uart_tx,output wire timer_irq,output wire[1:0] gpio_out,
 output reg[31:0] tohost, input wire ddr_ready,input wire[31:0] ddr_reads,ddr_writes,ddr_hits,ddr_wait);
 wire ib0=ia<32'h00018000,ib1=ia>=32'h10000000 && ia<32'h10020000;
 wire db0=da<32'h00018000,db1=da>=32'h10000000 && da<32'h10020000;
 reg game_xiangqi;
 wire gomoku_select=da[31:14]==(32'h20008000>>14);
 wire[31:0] gomoku_data;
 gomoku_eval #(.PATTERN_FILE("memory/pattern.hex")) evaluator(.clk(clk),.rst_n(rst_n),
  .command(dwrite && dr && wa==32'h20008004 && &dm),.command_data(dw),
  .read(da_fire && !dwrite && gomoku_select),.read_offset(da[13:0]),.rdata(gomoku_data),.busy());
 reg gomoku_response;
 reg ipending,ibank,ierror;reg dpending,dbank,derror;reg[4:0] response_select;reg[31:0] mmio_data;
 wire[63:0] iq0,iq1,dq0,dq1;

 wire uart_ready;wire uart_addr=wa==32'h20000000;
 wire uart_send=dv && dr && dwrite && uart_addr && dm[0];
 nc_uart #(.CLOCK_HZ(CLOCK_HZ)) uart(.clk(clk),.rst_n(rst_n),.send(uart_send),.data(dw[7:0]),.ready(uart_ready),.tx(uart_tx));
 assign dr=rst_n && (!dpending || dor) && !(dwrite && uart_addr && !uart_ready) &&
  !(dv && !dwrite && da==32'h20005000 && !attack_ready) &&
  !(dv && !dwrite && da==32'h20005008 && !ray_ready);
 wire da_fire=dv && dr;
 wire attack_ready;wire[1:0] attack_checks;
 nc_attack_check attack(.clk(clk),.rst_n(rst_n),.write_valid(game_xiangqi && dwrite && dr && wb1),
  .write_address(wa),.write_data(dw),.write_mask(dm),.ready(attack_ready),.checks(attack_checks));
 wire ray_ready;wire[31:0] ray_result;
 nc_ray_targets ray(.clk(clk),.rst_n(rst_n),.write_valid(game_xiangqi && dwrite && dr && wb1),
  .write_address(wa),.write_data(dw),.write_mask(dm),
  .request(game_xiangqi && dwrite && dr && wa==32'h20005004 && dm[0] && dm[1]),
  .source(dw[7:0]),.second(dw[8]),.side(dw[9]),.ready(ray_ready),.result(ray_result));
 wire [7:0] rx_data;wire [6:0] rx_count;wire rx_available,rx_overflow,rx_framing;
 wire rx_pop=da_fire && !dwrite && da==32'h2000000c;
 wire rx_clear=dwrite && dr && wa==32'h20000008 && dm[0];
 nc_uart_rx #(.CLOCK_HZ(CLOCK_HZ)) uart_rx_unit(.clk(clk),.rst_n(rst_n),.rx(uart_rx),.pop(rx_pop),
 .clear_overflow(rx_clear && dw[1]),.clear_framing(rx_clear && dw[2]),
 .data(rx_data),.available(rx_available),.count(rx_count),.overflow(rx_overflow),.framing_error(rx_framing));
 // Avoid undefined cross-port read-during-write on the same physical word.
 // FENCE.I discards previously fetched words for self-modifying code.
 // dwrite is a published-write qualifier: it implies dv. Its address is
 // registered in MEM, so EX load/branch data cannot enter IF collision control.
 wire wb0=wa<32'h00018000,wb1=wa>=32'h10000000 && wa<32'h10020000;
 wire collision=dr && dwrite && ((ib0 && wb0)||(ib1 && wb1)) && ia[16:3]==wa[16:3];
 assign ir=rst_n && (!ipending || ior) && !collision;
 wire ia_fire=iv && ir;
 assign iov=ipending;assign ierr=ierror;assign idata=ibank ? iq1 : iq0;
 assign dov=dpending;assign derr=derror;assign dline=dbank ? dq1 : dq0;// Register bank/half/MMIO selection at request acceptance, before RAM data arrives.
 assign ddata=({32{response_select[0]}} & dq0[31:0]) |
              ({32{response_select[1]}} & dq0[63:32]) |
              ({32{response_select[2]}} & dq1[31:0]) |
              ({32{response_select[3]}} & dq1[63:32]) |
              ({32{response_select[4] && !gomoku_response}} & mmio_data) |
              ({32{gomoku_response}} & gomoku_data);
 reg[63:0] mtime,mtimecmp;reg[1:0] gpio;
 assign timer_irq=mtime>=mtimecmp;assign gpio_out=gpio;
 reg mmio_known;reg[31:0] read_mmio;
 always @* begin
  mmio_known=1;read_mmio=0;
  case(da)
   32'h20006000:read_mmio={31'b0,game_xiangqi};
   32'h20005000:read_mmio={30'b0,attack_checks};
   32'h20005004:read_mmio=0;
   32'h20005008:read_mmio=ray_result;
   32'h20004000:read_mmio={31'b0,ddr_ready};
   32'h20004004:read_mmio=0;
   32'h20004008:read_mmio=ddr_reads;32'h2000400c:read_mmio=ddr_writes;
   32'h20004010:read_mmio=ddr_hits;32'h20004014:read_mmio=ddr_wait;
   32'h20000000:read_mmio=0;
   32'h20000004:read_mmio={31'b0,uart_ready};
   32'h20000008:read_mmio={17'd0,rx_count,5'd0,rx_framing,rx_overflow,rx_available};
   32'h2000000c:read_mmio={24'd0,rx_data};
   32'h20001000:read_mmio=mtime[31:0];32'h20001004:read_mmio=mtime[63:32];
   32'h20001008:read_mmio=mtimecmp[31:0];32'h2000100c:read_mmio=mtimecmp[63:32];
   32'h20002000:read_mmio={30'b0,gpio};32'h20003000:read_mmio=tohost;
   default:mmio_known=gomoku_select;
  endcase
 end
 integer j;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   game_xiangqi<=0;gomoku_response<=0;ipending<=0;ibank<=0;ierror<=0;dpending<=0;dbank<=0;response_select<=5'b10000;derror<=0;mmio_data<=0;
   mtime<=0;mtimecmp<=64'hffffffffffffffff;gpio<=0;tohost<=0;
  end else begin
   mtime<=mtime+1'b1;
   if(ia_fire) begin ipending<=1;ibank<=ib1;ierror<=!(ib0 || ib1) || |ia[1:0];end
   else if(iov && ior) ipending<=0;
   if(da_fire) begin
    gomoku_response<=gomoku_select;dpending<=1;dbank<=db1;response_select<={!(db0 || db1),db1 && da[2],db1 && !da[2],db0 && da[2],db0 && !da[2]};derror<=!(db0 || db1 || mmio_known);mmio_data<=read_mmio;
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
     if(wa==32'h20006000 && dm[0]) game_xiangqi<=dw[0];
     if(wa==32'h20002000 && dm[0]) gpio<=dw[1:0];
   end
  end
 end
 nc_code_ram ram_code(.a_clk(clk),.a_rst(!rst_n),.a_clk_en(ia_fire && ib0 && !ia[1] && !ia[0]),
  .a_addr(ia[16:3]),.a_wr_data(64'b0),.a_wr_en(1'b0),.a_wr_byte_en(8'b0),.a_rd_data(iq0),
  .b_clk(clk),.b_rst(!rst_n),.b_clk_en(da_fire && db0),.b_addr(da[16:3]),
  .b_wr_data({dw,dw}),.b_wr_en(dwrite),.b_wr_byte_en(!dwrite ? 8'hff : wa[2] ? {dm,4'b0} : {4'b0,dm}),.b_rd_data(dq0));

 ram2_tdp ram_data(.a_clk(clk),.a_rst(!rst_n),.a_clk_en(ia_fire && ib1 && !ia[1] && !ia[0]),
  .a_addr(ia[16:3]),.a_wr_data(64'b0),.a_wr_en(1'b0),.a_wr_byte_en(8'b0),.a_rd_data(iq1),
  .b_clk(clk),.b_rst(!rst_n),.b_clk_en(da_fire && db1),.b_addr(da[16:3]),
  .b_wr_data({dw,dw}),.b_wr_en(dwrite),.b_wr_byte_en(!dwrite ? 8'hff : wa[2] ? {dm,4'b0} : {4'b0,dm}),.b_rd_data(dq1));

endmodule
