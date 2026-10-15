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

// Registered fetch frontend: no RAM-response bypass into ID and no ID-ready
// path into the outgoing command. Each prepared/accepted command reserves a
// FIFO slot. One response and the next command may turn over on the same edge.
(* syn_state_machine = 0 *)
module ifu_p5 #(
    parameter FIFO_DEPTH = 4
)(
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
    localparam PTR_WIDTH = FIFO_DEPTH>1 ? $clog2(FIFO_DEPTH) : 1;
    localparam COUNT_WIDTH = $clog2(FIFO_DEPTH+1);
    reg[31:0] next_pc_q, cmd_pc_q, pending_pc;
    reg cmd_valid, cmd_discard;
    reg pending, discard;
    reg[1:0] pending_fault;
    reg[31:0] fifo_inst[0:FIFO_DEPTH-1], fifo_pc[0:FIFO_DEPTH-1];
    reg[1:0] fifo_fault[0:FIFO_DEPTH-1];
    reg[PTR_WIDTH-1:0] rd_ptr, wr_ptr;
    reg[COUNT_WIDTH-1:0] count;
    // Debug alias retained for existing SoC observation scripts.
    wire[31:0] pc = next_pc_q;
    wire response = pending && (pending_fault!=0 || rsp_valid_i);
    wire good_response = response && !discard && !flush_i;
    assign valid_o = !flush_i && count!=0;
    assign inst_o = fifo_inst[rd_ptr];
    assign pc_o = fifo_pc[rd_ptr];
    assign fault_o = fifo_fault[rd_ptr];
    wire pop = valid_o && ready_i;
    wire push = good_response;
    wire[COUNT_WIDTH+1:0] reserved = {2'b0,count} + pending + cmd_valid;
    wire[1:0] address_fault = |cmd_pc_q[1:0] ? 2'd1 :
        (cmd_pc_q[31:28]>1 ? 2'd2 : 2'd0);
    wire issue = rst_n && cmd_valid && (!pending || response);
    // Flush/stop never withdraw a published, unaccepted command. Its reply
    // is drained using sticky discard bits; repeated redirects cannot revive it.
    assign req_valid_o = issue && address_fault==0;
    wire accepted = issue && (address_fault!=0 || req_ready_i);
    // Deliberately use registered occupancy, not pop/ready_i, for new credit.
    // A response transfers its existing reservation into the FIFO.
    wire prepare = !stop_i && !flush_i && (!cmd_valid || accepted) &&
        reserved < FIFO_DEPTH;
    assign addr_o = cmd_pc_q;
    assign rsp_ready_o = 1'b1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            next_pc_q<=`CPU_RESET_ADDR; cmd_pc_q<=0; pending_pc<=0;
            cmd_valid<=0; cmd_discard<=0;
            pending<=0; discard<=0; pending_fault<=0;
            count<=0; rd_ptr<=0; wr_ptr<=0;
        end else begin
            if (accepted) begin
                pending<=1; pending_pc<=cmd_pc_q; pending_fault<=address_fault;
                discard<=cmd_discard || flush_i;
                cmd_valid<=0; cmd_discard<=0;
            end else if (response) begin pending<=0; discard<=0; end
            if (prepare) begin
                cmd_valid<=1; cmd_discard<=0; cmd_pc_q<=next_pc_q;
                next_pc_q<=next_pc_q+32'd4;
            end
            if (flush_i) begin
                next_pc_q<=flush_addr_i; count<=0; rd_ptr<=0; wr_ptr<=0;
                if (cmd_valid && !accepted) cmd_discard<=1;
                if (pending && !response && !accepted) discard<=1;
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
                    wr_ptr<=wr_ptr==FIFO_DEPTH-1 ? 0 : wr_ptr+1'b1;
                end
                if (pop) rd_ptr<=rd_ptr==FIFO_DEPTH-1 ? 0 : rd_ptr+1'b1;
            end
        end
    end
endmodule
