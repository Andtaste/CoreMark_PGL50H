module top(input wire clk,rst_ext_i,uart_rx_pin,output wire uart_tx_pin,
 output wire ddr_ready_led,halted_ind,heartbeat_led,pll_lock_led,
 output wire mem_rst_n,mem_ck,mem_ck_n,mem_cke,mem_cs_n,mem_ras_n,mem_cas_n,mem_we_n,mem_odt,
 output wire[14:0] mem_a,output wire[2:0] mem_ba,
 inout wire[3:0] mem_dqs,mem_dqs_n,inout wire[31:0] mem_dq,output wire[3:0] mem_dm);
 wire cpu_clk,cpu_locked,ui_clk,ddr_locked,ddr_initialized,ddr_ready;
 wire base_reset_n=rst_ext_i && cpu_locked;
 wire ui_reset_n=base_reset_n && ddr_locked;
 pll cpu_clock(.clkin1(clk),.clkout0(cpu_clk),.pll_lock(cpu_locked));
 wire cpu_reset_n;
 nc_platform_reset reset_control(.clk(cpu_clk),.base_reset_n(base_reset_n),.ddr_ready(ddr_ready),.cpu_rst_n(cpu_reset_n));
 reg[25:0] heartbeat;
 always @(posedge cpu_clk or negedge base_reset_n)if(!base_reset_n)heartbeat<=0;else heartbeat<=heartbeat+1'b1;
 assign heartbeat_led=heartbeat[25];assign pll_lock_led=cpu_locked && ddr_locked;assign ddr_ready_led=ddr_ready;
 wire[31:0] tohost;assign halted_ind=tohost!=0;
 wire ext_valid,ext_ready,ext_write,ext_clear,ext_rsp_valid,ext_rsp_ready;
 wire[23:0] ext_address;wire[31:0] ext_data;wire[3:0] ext_mask;wire[63:0] ext_rsp_line;
 wire[31:0] reads,writes,hits,wait_cycles;
 nc_soc #(.CLOCK_HZ(91000000)) soc(.clk(cpu_clk),.rst_n(cpu_reset_n),.uart_rx(uart_rx_pin),.uart_tx(uart_tx_pin),
 .irq_soft(1'b0),.irq_ext(1'b0),.gpio_out(),.tohost(tohost),.ddr_ready(ddr_ready),.ddr_reads(reads),.ddr_writes(writes),.ddr_hits(hits),.ddr_wait(wait_cycles),
 .ext_valid(ext_valid),.ext_ready(ext_ready),.ext_write(ext_write),.ext_clear(ext_clear),.ext_address(ext_address),.ext_data(ext_data),.ext_mask(ext_mask),
 .ext_rsp_valid(ext_rsp_valid),.ext_rsp_ready(ext_rsp_ready),.ext_rsp_line(ext_rsp_line));
 wire[27:0] awaddr,araddr;wire[3:0] awlen,arlen;
 wire awvalid,awready,wready,arvalid,arready,rvalid,rlast;
 wire[255:0] wdata,rdata;wire[31:0] wstrb;
 nc_ddr_bridge bridge(.clk(cpu_clk),.rst_n(base_reset_n),.req_valid(ext_valid),.req_ready(ext_ready),.req_write(ext_write),.req_clear(ext_clear),
 .req_address(ext_address),.req_data(ext_data),.req_mask(ext_mask),.rsp_valid(ext_rsp_valid),.rsp_ready(ext_rsp_ready),.rsp_line(ext_rsp_line),
 .ready(ddr_ready),.reads(reads),.writes(writes),.cache_hits(hits),.wait_cycles(wait_cycles),
 .ui_clk(ui_clk),.ui_rst_n(ui_reset_n),.init_done(ddr_initialized),
 .axi_awaddr(awaddr),.axi_awlen(awlen),.axi_awvalid(awvalid),.axi_awready(awready),.axi_wdata(wdata),.axi_wstrb(wstrb),.axi_wready(wready),
 .axi_araddr(araddr),.axi_arlen(arlen),.axi_arvalid(arvalid),.axi_arready(arready),.axi_rdata(rdata),.axi_rvalid(rvalid),.axi_rlast(rlast));
 // Preserve the factory hierarchy name used by DDR PHY placement constraints.
 ddr3_test I_ipsxb_ddr_top(.ref_clk(clk),.resetn(rst_ext_i),.ddr_init_done(ddr_initialized),.ddrphy_clkin(ui_clk),.pll_lock(ddr_locked),
 .axi_awaddr(awaddr),.axi_awuser_ap(1'b0),.axi_awuser_id(4'b0),.axi_awlen(awlen),.axi_awready(awready),.axi_awvalid(awvalid),
 .axi_wdata(wdata),.axi_wstrb(wstrb),.axi_wready(wready),.axi_wusero_id(),.axi_wusero_last(),
 .axi_araddr(araddr),.axi_aruser_ap(1'b0),.axi_aruser_id(4'b0),.axi_arlen(arlen),.axi_arready(arready),.axi_arvalid(arvalid),
 .axi_rdata(rdata),.axi_rid(),.axi_rlast(rlast),.axi_rvalid(rvalid),
 .apb_clk(1'b0),.apb_rst_n(1'b0),.apb_sel(1'b0),.apb_enable(1'b0),.apb_addr(8'b0),.apb_write(1'b0),.apb_ready(),.apb_wdata(16'b0),.apb_rdata(),.apb_int(),
 .debug_data(),.debug_slice_state(),.debug_calib_ctrl(),.ck_dly_set_bin(),.force_ck_dly_en(1'b0),.force_ck_dly_set_bin(8'b0),
 .dll_step(),.dll_lock(),.init_read_clk_ctrl(2'b0),.init_slip_step(4'b0),.force_read_clk_ctrl(1'b0),.ddrphy_gate_update_en(1'b0),.update_com_val_err_flag(),.rd_fake_stop(1'b0),
 .mem_rst_n(mem_rst_n),.mem_ck(mem_ck),.mem_ck_n(mem_ck_n),.mem_cke(mem_cke),.mem_cs_n(mem_cs_n),.mem_ras_n(mem_ras_n),
 .mem_cas_n(mem_cas_n),.mem_we_n(mem_we_n),.mem_odt(mem_odt),.mem_a(mem_a),.mem_ba(mem_ba),.mem_dqs(mem_dqs),.mem_dqs_n(mem_dqs_n),.mem_dq(mem_dq),.mem_dm(mem_dm));
endmodule
