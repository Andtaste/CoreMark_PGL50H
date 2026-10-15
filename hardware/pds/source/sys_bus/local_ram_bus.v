// Local single-port RAM paths plus a shared peripheral bus.
// Inspired by RVCoreP's separate synchronous I/D RAM connections; our existing
// single-port IPs still need arbitration for CPU cross-access and JTAG SBA.
// Every master/port has at most one outstanding transaction. Replies use the
// accepted owner, never the current request. RAM paths do not traverse RIB.
module local_ram_bus(
    input wire clk,
    input wire rst_n,

    // master 0 interface
    input wire[31:0] m0_addr_i,
    input wire[31:0] m0_data_i,
    input wire[3:0] m0_sel_i,
    input wire m0_req_vld_i,
    input wire m0_rsp_rdy_i,
    input wire m0_we_i,
    output wire m0_req_rdy_o,
    output wire m0_rsp_vld_o,
    output wire[31:0] m0_data_o,

    // master 1 interface
    input wire[31:0] m1_addr_i,
    input wire[31:0] m1_data_i,
    input wire[3:0] m1_sel_i,
    input wire m1_req_vld_i,
    input wire m1_rsp_rdy_i,
    input wire m1_we_i,
    output wire m1_req_rdy_o,
    output wire m1_rsp_vld_o,
    output wire[31:0] m1_data_o,

    // master 2 interface
    input wire[31:0] m2_addr_i,
    input wire[31:0] m2_data_i,
    input wire[3:0] m2_sel_i,
    input wire m2_req_vld_i,
    input wire m2_rsp_rdy_i,
    input wire m2_we_i,
    output wire m2_req_rdy_o,
    output wire m2_rsp_vld_o,
    output wire[31:0] m2_data_o,

    // slave 0 interface
    input wire[31:0] s0_data_i,
    input wire s0_req_rdy_i,
    input wire s0_rsp_vld_i,
    output wire[31:0] s0_addr_o,
    output wire[31:0] s0_data_o,
    output wire[3:0] s0_sel_o,
    output wire s0_req_vld_o,
    output wire s0_rsp_rdy_o,
    output wire s0_we_o,

    // slave 1 interface
    input wire[31:0] s1_data_i,
    input wire s1_req_rdy_i,
    input wire s1_rsp_vld_i,
    output wire[31:0] s1_addr_o,
    output wire[31:0] s1_data_o,
    output wire[3:0] s1_sel_o,
    output wire s1_req_vld_o,
    output wire s1_rsp_rdy_o,
    output wire s1_we_o,

    // slave 2 interface
    input wire[31:0] s2_data_i,
    input wire s2_req_rdy_i,
    input wire s2_rsp_vld_i,
    output wire[31:0] s2_addr_o,
    output wire[31:0] s2_data_o,
    output wire[3:0] s2_sel_o,
    output wire s2_req_vld_o,
    output wire s2_rsp_rdy_o,
    output wire s2_we_o,

    // slave 3 interface
    input wire[31:0] s3_data_i,
    input wire s3_req_rdy_i,
    input wire s3_rsp_vld_i,
    output wire[31:0] s3_addr_o,
    output wire[31:0] s3_data_o,
    output wire[3:0] s3_sel_o,
    output wire s3_req_vld_o,
    output wire s3_rsp_rdy_o,
    output wire s3_we_o,

    // slave 4 interface
    input wire[31:0] s4_data_i,
    input wire s4_req_rdy_i,
    input wire s4_rsp_vld_i,
    output wire[31:0] s4_addr_o,
    output wire[31:0] s4_data_o,
    output wire[3:0] s4_sel_o,
    output wire s4_req_vld_o,
    output wire s4_rsp_rdy_o,
    output wire s4_we_o

    );



    wire [31:0] addr[0:2], wdata[0:2];
    wire [3:0] byte_en[0:2];
    wire [2:0] request, write_en, rsp_ready;
    wire [31:0] rdata[0:2];
    wire [2:0] ready, rsp_valid;
    assign addr[0]=m0_addr_i; assign addr[1]=m1_addr_i; assign addr[2]=m2_addr_i;
    assign wdata[0]=m0_data_i; assign wdata[1]=m1_data_i; assign wdata[2]=m2_data_i;
    assign byte_en[0]=m0_sel_i; assign byte_en[1]=m1_sel_i; assign byte_en[2]=m2_sel_i;
    assign request={m2_req_vld_i,m1_req_vld_i,m0_req_vld_i};
    assign write_en={m2_we_i,m1_we_i,m0_we_i};
    assign rsp_ready={m2_rsp_rdy_i,m1_rsp_rdy_i,m0_rsp_rdy_i};

    // Ports 0/1 are the physical RAMs. Port 2 is one shared MMIO bus.
    wire [31:0] p_addr[0:2], p_data[0:2], p_rdata[0:2];
    wire [3:0] p_sel[0:2];
    wire [2:0] p_req, p_we, p_ready, p_valid, p_rsp_ready;
    wire [2:0] pending;
    wire [1:0] owner[0:2];
    wire [2:0] master_free;
    reg [1:0] peripheral_target;

    assign p_ready[0]=s0_req_rdy_i; assign p_ready[1]=s1_req_rdy_i;
    assign p_rdata[0]=s0_data_i; assign p_rdata[1]=s1_data_i;
    assign p_valid[0]=s0_rsp_vld_i; assign p_valid[1]=s1_rsp_vld_i;
    assign p_ready[2]=p_addr[2][31:28]==2 ? s2_req_rdy_i :
                      p_addr[2][31:28]==3 ? s3_req_rdy_i : s4_req_rdy_i;
    assign p_rdata[2]=peripheral_target==0 ? s2_data_i :
                      peripheral_target==1 ? s3_data_i : s4_data_i;
    assign p_valid[2]=peripheral_target==0 ? s2_rsp_vld_i :
                      peripheral_target==1 ? s3_rsp_vld_i : s4_rsp_vld_i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) peripheral_target<=0;
        else if (p_req[2] && p_ready[2]) peripheral_target<=p_addr[2][29:28]-2'd2;
    end

    genvar m,p;
    generate for(m=0;m<3;m=m+1) begin: master_port
        wire [2:0] blocked;
        wire [2:0] selected_rsp;
        wire [2:0] request_ready;
        for(p=0;p<3;p=p+1) begin: route
            // Readiness is for this master's target, before address arbitration.
            // Using p_ready[2] here would let chosen/p_addr feed the master's
            // own valid indirectly back into ready, despite eligible being
            // independent of that valid. The winner still uses p_ready below
            // for the actual physical-port acceptance and response ownership.
            wire target_ready=(p==0) ? s0_req_rdy_i : (p==1) ? s1_req_rdy_i :
                addr[m][31:28]==2 ? s2_req_rdy_i :
                addr[m][31:28]==3 ? s3_req_rdy_i : s4_req_rdy_i;
            assign blocked[p]=pending[p] && owner[p]==m &&
                !(p_valid[p] && rsp_ready[m]);
            assign selected_rsp[p]=pending[p] && owner[p]==m;
            assign request_ready[p]=ram_port[p].eligible[m] &&
                ram_port[p].available && target_ready &&
                (m==2 ? 1'b1 : m==1 ? !ram_port[p].candidate[2] :
                 !(ram_port[p].candidate[2] || ram_port[p].candidate[1]));
        end
        assign master_free[m]=!(|blocked);
        // A master's ready does not depend on its own valid/ID consume path.
        assign ready[m]=rst_n && (|request_ready);
        assign rsp_valid[m]=|(selected_rsp & p_valid);
        assign rdata[m]=({32{selected_rsp[0]}} & p_rdata[0]) |
                        ({32{selected_rsp[1]}} & p_rdata[1]) |
                        ({32{selected_rsp[2]}} & p_rdata[2]);
    end endgenerate

    generate for(p=0;p<3;p=p+1) begin: ram_port
        wire [2:0] eligible,candidate;
        wire available=!pending[p] || (p_valid[p] && p_rsp_ready[p]);
        for(m=0;m<3;m=m+1) begin: decode
            // IF executes only RAM1/RAM2; MMIO is for LSU and JTAG.
            wire match_addr=(p<2) ? addr[m][31:28]==p :
                (m!=0 && addr[m][31:28]>=2 && addr[m][31:28]<=4);
            assign eligible[m]=master_free[m] && match_addr;
            assign candidate[m]=request[m] && eligible[m];
        end
        // Default to the normal local source even when idle: IF for RAM1,
        // LSU for RAM2/MMIO. Only shared accesses need to select another source.
        wire [1:0] chosen=candidate[2] ? 2'd2 : candidate[1] ? 2'd1 :
                          candidate[0] ? 2'd0 : (p==0 ? 2'd0 : 2'd1);
        assign p_addr[p]=addr[chosen];
        assign p_data[p]=wdata[chosen];
        assign p_sel[p]=byte_en[chosen];
        assign p_req[p]=rst_n && available && (|candidate);
        assign p_we[p]=p_req[p] && write_en[chosen];
        assign p_rsp_ready[p]=pending[p] ? rsp_ready[owner[p]] : 1'b1;
        reg pending_q;
        reg [1:0] owner_q /* synthesis syn_state_machine = 0 */;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin pending_q<=0; owner_q<=0; end
            else if (p_req[p] && p_ready[p]) begin pending_q<=1; owner_q<=chosen; end
            else if (p_valid[p] && p_rsp_ready[p]) pending_q<=0;
        end
        assign pending[p]=pending_q;
        assign owner[p]=owner_q;
    end endgenerate

    assign m0_req_rdy_o=ready[0]; assign m0_rsp_vld_o=rsp_valid[0]; assign m0_data_o=rdata[0];
    assign m1_req_rdy_o=ready[1]; assign m1_rsp_vld_o=rsp_valid[1]; assign m1_data_o=rdata[1];
    assign m2_req_rdy_o=ready[2]; assign m2_rsp_vld_o=rsp_valid[2]; assign m2_data_o=rdata[2];
    assign s0_addr_o={4'b0,p_addr[0][27:0]}; assign s0_data_o=p_data[0]; assign s0_sel_o=p_sel[0];
    assign s0_req_vld_o=p_req[0]; assign s0_we_o=p_we[0]; assign s0_rsp_rdy_o=p_rsp_ready[0];
    assign s1_addr_o={4'b0,p_addr[1][27:0]}; assign s1_data_o=p_data[1]; assign s1_sel_o=p_sel[1];
    assign s1_req_vld_o=p_req[1]; assign s1_we_o=p_we[1]; assign s1_rsp_rdy_o=p_rsp_ready[1];
    assign s2_addr_o={4'b0,p_addr[2][27:0]};
    assign s2_data_o=p_data[2]; assign s2_sel_o=p_sel[2];
    assign s2_req_vld_o=p_req[2] && p_addr[2][31:28]==2;
    assign s2_we_o=p_we[2] && p_addr[2][31:28]==2;
    assign s2_rsp_rdy_o=p_rsp_ready[2] && peripheral_target==0;
    assign s3_addr_o={4'b0,p_addr[2][27:0]};
    assign s3_data_o=p_data[2]; assign s3_sel_o=p_sel[2];
    assign s3_req_vld_o=p_req[2] && p_addr[2][31:28]==3;
    assign s3_we_o=p_we[2] && p_addr[2][31:28]==3;
    assign s3_rsp_rdy_o=p_rsp_ready[2] && peripheral_target==1;
    assign s4_addr_o={4'b0,p_addr[2][27:0]};
    assign s4_data_o=p_data[2]; assign s4_sel_o=p_sel[2];
    assign s4_req_vld_o=p_req[2] && p_addr[2][31:28]==4;
    assign s4_we_o=p_we[2] && p_addr[2][31:28]==4;
    assign s4_rsp_rdy_o=p_rsp_ready[2] && peripheral_target==2;
endmodule
