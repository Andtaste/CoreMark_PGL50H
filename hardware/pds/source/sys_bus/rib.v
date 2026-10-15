 /*                                                                      
 Copyright 2020 Blue Liang, liangkangnan@163.com
                                                                         
 Licensed under the Apache License, Version 2.0 (the "License");         
 you may not use this file except in compliance with the License.        
 You may obtain a copy of the License at                                 
                                                                         
     http://www.apache.org/licenses/LICENSE-2.0                          
                                                                         
 Unless required by applicable law or agreed to in writing, software    
 distributed under the License is distributed on an "AS IS" BASIS,       
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and     
 limitations under the License.                                          
 */


// RIB总线模块
module rib #(
    parameter MASTER_NUM = 3,
    parameter SLAVE_NUM = 2,
    parameter PARALLEL_ACCESS = 0,
    parameter REGISTERED_RESPONSE = 0)(

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

    // master 3 interface
    input wire[31:0] m3_addr_i,
    input wire[31:0] m3_data_i,
    input wire[3:0] m3_sel_i,
    input wire m3_req_vld_i,
    input wire m3_rsp_rdy_i,
    input wire m3_we_i,
    output wire m3_req_rdy_o,
    output wire m3_rsp_vld_o,
    output wire[31:0] m3_data_o,

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


    // REGISTERED_RESPONSE=0 retains the old current-grant routing for unit
    // comparison only. The five-stage SoC selects 1: request arbitration is
    // combinational and response owners are registered until completion.
    // Capacity is one outstanding command per master and per slave, with
    // same-cycle response completion / next request acceptance supported.
    // Priority is unchanged: m2 (JTAG) > m1 (data) > m0 (fetch), m3 if enabled
    // has the highest priority, matching the original reversed packing.
    wire[31:0] m_addr[0:3];
    wire[31:0] m_wdata[0:3];
    wire[3:0] m_sel[0:3];
    wire[3:0] m_req;
    wire[3:0] m_we;
    wire[3:0] m_rsp_ready;
    wire[31:0] m_rdata[0:3];
    wire[3:0] m_ready;
    wire[3:0] m_rsp_valid;
    assign m_addr[0] = m0_addr_i;
    assign m_addr[1] = m1_addr_i;
    assign m_addr[2] = m2_addr_i;
    assign m_addr[3] = m3_addr_i;
    assign m_wdata[0] = m0_data_i;
    assign m_wdata[1] = m1_data_i;
    assign m_wdata[2] = m2_data_i;
    assign m_wdata[3] = m3_data_i;
    assign m_sel[0] = m0_sel_i;
    assign m_sel[1] = m1_sel_i;
    assign m_sel[2] = m2_sel_i;
    assign m_sel[3] = m3_sel_i;
    assign m_req = {m3_req_vld_i, m2_req_vld_i, m1_req_vld_i, m0_req_vld_i};
    assign m_we = {m3_we_i, m2_we_i, m1_we_i, m0_we_i};
    assign m_rsp_ready = {m3_rsp_rdy_i, m2_rsp_rdy_i, m1_rsp_rdy_i, m0_rsp_rdy_i};

    wire[31:0] s_rdata[0:4];
    wire[4:0] s_ready;
    wire[4:0] s_rsp_valid;
    wire[31:0] s_addr[0:4];
    wire[31:0] s_wdata[0:4];
    wire[3:0] s_sel[0:4];
    wire[4:0] s_req;
    wire[4:0] s_we;
    wire[4:0] s_rsp_ready;
    assign s_rdata[0] = s0_data_i;
    assign s_rdata[1] = s1_data_i;
    assign s_rdata[2] = s2_data_i;
    assign s_rdata[3] = s3_data_i;
    assign s_rdata[4] = s4_data_i;
    assign s_ready = {s4_req_rdy_i, s3_req_rdy_i, s2_req_rdy_i, s1_req_rdy_i, s0_req_rdy_i};
    assign s_rsp_valid = {s4_rsp_vld_i, s3_rsp_vld_i, s2_rsp_vld_i, s1_rsp_vld_i, s0_rsp_vld_i};

    // Five-stage protocol: one outstanding transaction per master. A slave
    // remembers the accepted owner until the response handshakes. Completion
    // and the next acceptance may occur together, preserving 1/cycle fetch.
    wire[4:0] rsp_pending;
    wire[1:0] rsp_owner[0:4];
    wire[3:0] master_available;
    genvar a, b;
    generate for (a=0; a<4; a=a+1) begin: outstanding_master
        wire[SLAVE_NUM-1:0] blocked;
        for (b=0; b<SLAVE_NUM; b=b+1) begin: outstanding_slave
            assign blocked[b] = rsp_pending[b] && (rsp_owner[b] == a) &&
                !(s_rsp_valid[b] && m_rsp_ready[a]);
        end
        assign master_available[a] = !REGISTERED_RESPONSE || !(|blocked);
    end endgenerate

    wire[MASTER_NUM-1:0] candidates[0:SLAVE_NUM-1];
    wire[MASTER_NUM-1:0] grant[0:SLAVE_NUM-1];
    genvar s, m;
    generate
        for (s = 0; s < 5; s = s + 1) begin: slave_port
            if (s < SLAVE_NUM) begin: active
                for (m = 0; m < MASTER_NUM; m = m + 1) begin: arbitration
                    wire target_match = (m_addr[m][31:28] == s);
                    // Legacy mode considers all requesting masters before
                    // decoding; parallel mode arbitrates only this slave.
                    assign candidates[s][m] = m_req[m] & master_available[m] &
                        ((PARALLEL_ACCESS == 0) | target_match);
                    if (m == MASTER_NUM - 1) begin: highest
                        assign grant[s][m] = candidates[s][m] & target_match;
                    end else begin: lower
                        assign grant[s][m] = candidates[s][m] & target_match &
                            (~(|candidates[s][MASTER_NUM-1:m+1]));
                    end
                end
                integer k;
                reg[31:0] sum_addr, sum_data;
                reg[3:0] sum_sel;
                reg sum_req, sum_we, sum_ready;
                always @ (*) begin
                    sum_addr = 32'h0;
                    sum_data = 32'h0;
                    sum_sel = 4'h0;
                    sum_req = 1'b0;
                    sum_we = 1'b0;
                    sum_ready = 1'b0;
                    for (k = 0; k < MASTER_NUM; k = k + 1) begin
                        sum_addr = sum_addr | ({32{grant[s][k]}} & {4'h0, m_addr[k][27:0]});
                        sum_data = sum_data | ({32{grant[s][k]}} & m_wdata[k]);
                        sum_sel = sum_sel | ({4{grant[s][k]}} & m_sel[k]);
                        sum_req = sum_req | grant[s][k];
                        sum_we = sum_we | (grant[s][k] & m_we[k]);
                        sum_ready = sum_ready | (grant[s][k] & m_rsp_ready[k]);
                    end
                end
                assign s_addr[s] = sum_addr;
                assign s_wdata[s] = sum_data;
                assign s_sel[s] = sum_sel;
                assign s_req[s] = sum_req;
                assign s_we[s] = sum_we;
                assign s_rsp_ready[s] = REGISTERED_RESPONSE ?
                    (rsp_pending[s] ? m_rsp_ready[rsp_owner[s]] : 1'b1) : sum_ready;
                if (REGISTERED_RESPONSE) begin: response_owner
                    reg pending;
                    reg[1:0] owner /* synthesis syn_state_machine = 0 */;
                    integer r;
                    always @(posedge clk or negedge rst_n) begin
                        if (!rst_n) begin pending<=0; owner<=0; end
                        else if (s_req[s] && s_ready[s]) begin
                            pending<=1;
                            for (r=0;r<MASTER_NUM;r=r+1)
                                if (grant[s][r]) owner<=r;
                        end else if (s_rsp_valid[s] && s_rsp_ready[s]) pending<=0;
                    end
                    assign rsp_pending[s]=pending;
                    assign rsp_owner[s]=owner;
                end else begin: legacy_owner
                    assign rsp_pending[s]=0;
                    assign rsp_owner[s]=0;
                end
            end else begin: inactive
                assign s_addr[s] = 32'h0;
                assign s_wdata[s] = 32'h0;
                assign s_sel[s] = 4'h0;
                assign rsp_pending[s] = 1'b0;
                assign rsp_owner[s] = 2'b0;
                assign s_req[s] = 1'b0;
                assign s_we[s] = 1'b0;
                assign s_rsp_ready[s] = 1'b0;
            end
        end
        for (m = 0; m < 4; m = m + 1) begin: master_port
            if (m < MASTER_NUM) begin: active
                reg[31:0] data;
                reg ready, valid;
                integer k;
                always @ (*) begin
                    data = 32'h0;
                    ready = 1'b0;
                    valid = 1'b0;
                    for (k = 0; k < SLAVE_NUM; k = k + 1) begin
                        data = data | ({32{REGISTERED_RESPONSE ? (rsp_pending[k] && rsp_owner[k]==m) : grant[k][m]}} & s_rdata[k]);
                        ready = ready | (grant[k][m] & s_ready[k]);
                        valid = valid | ((REGISTERED_RESPONSE ? (rsp_pending[k] && rsp_owner[k]==m) : grant[k][m]) & s_rsp_valid[k]);
                    end
                end
                assign m_rdata[m] = data;
                assign m_ready[m] = ready;
                assign m_rsp_valid[m] = valid;
            end else begin: inactive
                assign m_rdata[m] = 32'h0;
                assign m_ready[m] = 1'b0;
                assign m_rsp_valid[m] = 1'b0;
            end
        end
    endgenerate

    assign m0_data_o = m_rdata[0];
    assign m0_req_rdy_o = m_ready[0];
    assign m0_rsp_vld_o = m_rsp_valid[0];
    assign m1_data_o = m_rdata[1];
    assign m1_req_rdy_o = m_ready[1];
    assign m1_rsp_vld_o = m_rsp_valid[1];
    assign m2_data_o = m_rdata[2];
    assign m2_req_rdy_o = m_ready[2];
    assign m2_rsp_vld_o = m_rsp_valid[2];
    assign m3_data_o = m_rdata[3];
    assign m3_req_rdy_o = m_ready[3];
    assign m3_rsp_vld_o = m_rsp_valid[3];
    assign s0_addr_o = s_addr[0];
    assign s0_data_o = s_wdata[0];
    assign s0_sel_o = s_sel[0];
    assign s0_req_vld_o = s_req[0];
    assign s0_we_o = s_we[0];
    assign s0_rsp_rdy_o = s_rsp_ready[0];
    assign s1_addr_o = s_addr[1];
    assign s1_data_o = s_wdata[1];
    assign s1_sel_o = s_sel[1];
    assign s1_req_vld_o = s_req[1];
    assign s1_we_o = s_we[1];
    assign s1_rsp_rdy_o = s_rsp_ready[1];
    assign s2_addr_o = s_addr[2];
    assign s2_data_o = s_wdata[2];
    assign s2_sel_o = s_sel[2];
    assign s2_req_vld_o = s_req[2];
    assign s2_we_o = s_we[2];
    assign s2_rsp_rdy_o = s_rsp_ready[2];
    assign s3_addr_o = s_addr[3];
    assign s3_data_o = s_wdata[3];
    assign s3_sel_o = s_sel[3];
    assign s3_req_vld_o = s_req[3];
    assign s3_we_o = s_we[3];
    assign s3_rsp_rdy_o = s_rsp_ready[3];
    assign s4_addr_o = s_addr[4];
    assign s4_data_o = s_wdata[4];
    assign s4_sel_o = s_sel[4];
    assign s4_req_vld_o = s_req[4];
    assign s4_we_o = s_we[4];
    assign s4_rsp_rdy_o = s_rsp_ready[4];

endmodule
