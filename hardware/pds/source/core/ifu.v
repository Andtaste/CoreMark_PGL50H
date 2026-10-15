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

`include "defines.v"

// 取指模块
module ifu(

    input wire clk,
    input wire rst_n,

    input wire flush_i,
    input wire[31:0] flush_addr_i,             // 跳转地址
    input wire[`STALL_WIDTH-1:0] stall_i,      // 流水线暂停标志
    input wire jtag_halt_i,

    output wire[31:0] inst_o,
    output wire[31:0] pc_o,
    output wire inst_valid_o,
    output wire stat_bubble_o,

    output wire[31:0] ibus_addr_o,
    input wire[31:0] ibus_data_i,
    output wire[31:0] ibus_data_o,
    output wire[3:0] ibus_sel_o,
    output wire ibus_we_o,
    output wire req_valid_o,
    input wire req_ready_i,
    input wire rsp_valid_i,
    output wire rsp_ready_o

    );

    assign req_valid_o = (~rst_n)? 1'b0:
                         (flush_i)? 1'b0:
                         stall_i[`STALL_PC]? 1'b0:
                         jtag_halt_i? 1'b0:
                         1'b1;
    assign rsp_ready_o = (~rst_n)? 1'b0: 1'b1;

    wire ifu_req_hsked = (req_valid_o & req_ready_i);
    wire ifu_rsp_hsked = (rsp_valid_i & rsp_ready_o);

    // 在执行多周期指令或者请求不到总线时需要暂停
    wire stall = stall_i[`STALL_PC] | (~ifu_req_hsked);

    reg[31:0] pc;
    reg[31:0] pc_prev;

    always @ (posedge clk or negedge rst_n) begin
        // 复位
        if (!rst_n) begin
            pc <= `CPU_RESET_ADDR;
            pc_prev <= 32'h0;
        // 冲刷
        end else if (flush_i) begin
            pc <= flush_addr_i;
        // 暂停，取上一条指令
        end else if (stall) begin
            pc <= pc_prev;
        // 取下一条指令
        end else begin
            pc <= pc + 32'h4;
            pc_prev <= pc;
        end
    end

    wire[31:0] pc_r;
    // 将PC打一拍
    wire pc_ena = (~stall);
    gen_en_dff #(32) pc_dff(clk, rst_n, pc_ena, pc, pc_r);

    reg req_hasked_r;

    always @ (posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            req_hasked_r <= 1'b1;
        end else begin
            req_hasked_r <= ifu_req_hsked;
        end
    end

    wire req_switched = ifu_req_hsked & (~req_hasked_r);

    reg rsp_hasked_r;

    always @ (posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rsp_hasked_r <= 1'b1;
        end else begin
            rsp_hasked_r <= ifu_rsp_hsked;
        end
    end

    wire rsp_switched = ifu_rsp_hsked & (~rsp_hasked_r);

    // 总线切换有两种情况：
    // 1.访存地址位于指令存储器：当访存完成后，ifu_req_hsked和ifu_rsp_hsked信号会同时从0变为1
    // 2.访存地址不位于指令存储器：当访存完成后，ifu_req_hsked先从0变为1和ifu_rsp_hsked后从0变为1
    // 只有第2种情况下取出来的指令是有效的，这里要把这两种情况识别出来
    wire bus_switched = req_switched & rsp_switched;

    // 取指地址
    assign ibus_addr_o = pc;
    assign pc_o = pc_r;
    wire inst_valid = ifu_rsp_hsked & (~flush_i) & (~bus_switched);
    // A bubble admitted to IF/ID, excluding deliberate pipeline holds/flushes.
    assign stat_bubble_o = rst_n & (~stall_i[`STALL_ID]) &
                           (~flush_i) & (~jtag_halt_i) & (~inst_valid);
    assign inst_o = inst_valid? ibus_data_i: `INST_NOP;

    assign ibus_sel_o = 4'b1111;
    assign ibus_we_o = 1'b0;
    assign ibus_data_o = 32'h0;

endmodule

// Five-stage frontend. The synchronous instruction RAM itself supplies the
// normal IF/ID data register; two skid entries absorb downstream stalls.
// One request may be outstanding. Old-path responses are drained after a
// redirect, never reinterpreted as an instruction at the new PC.
// PC, queue pointers and request metadata are data registers, not encoded FSMs.
(* syn_state_machine = 0 *)
module ifu_p5(
    input wire clk, rst_n,
    input wire flush_i,
    input wire[31:0] flush_addr_i,
    input wire stop_i,
    output wire[31:0] inst_o, pc_o,
    output wire[1:0] fault_o,
    output wire valid_o,
    input wire ready_i,
    output wire[31:0] addr_o,
    output wire req_valid_o,
    input wire req_ready_i,
    input wire[31:0] rdata_i,
    input wire rsp_valid_i,
    output wire rsp_ready_o
);
    reg[31:0] pc, pending_pc;
    reg pending, discard;
    reg[1:0] pending_fault;
    reg[31:0] fifo_inst[0:1], fifo_pc[0:1];
    reg[1:0] fifo_fault[0:1];
    reg rd_ptr, wr_ptr;
    reg[1:0] count;
    wire response = pending && (pending_fault!=0 || rsp_valid_i);
    wire good_response = response && !discard && !flush_i;
    assign valid_o = !flush_i && (count!=0 || good_response);
    assign inst_o = count!=0 ? fifo_inst[rd_ptr] : rdata_i;
    assign pc_o = count!=0 ? fifo_pc[rd_ptr] : pending_pc;
    assign fault_o = count!=0 ? fifo_fault[rd_ptr] : pending_fault;
    wire consume = valid_o && ready_i;
    wire pop = consume && count!=0;
    wire push = good_response && !(consume && count==0);
    wire credit = ({1'b0,count} + pending) < (3'd2 + consume);
    wire[1:0] address_fault = |pc[1:0] ? 2'd1 :
        (pc[31:28]>1 ? 2'd2 : 2'd0);
    wire issue = rst_n && !stop_i && !flush_i && credit &&
        (!pending || response);
    assign req_valid_o = issue && address_fault==0;
    wire accepted = issue && (address_fault!=0 || req_ready_i);
    assign addr_o = pc;
    assign rsp_ready_o = 1'b1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pc<=`CPU_RESET_ADDR; pending_pc<=0;
            pending<=0; discard<=0; pending_fault<=0;
            count<=0; rd_ptr<=0; wr_ptr<=0;
        end else begin
            if (accepted) begin
                pending<=1; pending_pc<=pc; pending_fault<=address_fault;
                discard<=0; pc<=pc+32'd4;
            end else if (response) begin pending<=0; discard<=0; end
            if (flush_i) begin
                pc<=flush_addr_i; count<=0; rd_ptr<=0; wr_ptr<=0;
                if (pending && !response) discard<=1;
            end else begin
                case ({push,pop})
                    2'b10: count<=count+1'b1;
                    2'b01: count<=count-1'b1;
                    default: ;
                endcase
                if (push) begin
                    fifo_inst[wr_ptr]<=rdata_i;
                    fifo_pc[wr_ptr]<=pending_pc;
                    fifo_fault[wr_ptr]<=pending_fault;
                    wr_ptr<=!wr_ptr;
                end
                if (pop) rd_ptr<=!rd_ptr;
            end
        end
    end
endmodule
