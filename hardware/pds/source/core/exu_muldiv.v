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


module exu_muldiv(

    input wire clk,
    input wire rst_n,

    input wire[31:0] muldiv_op1_i,
    input wire[31:0] muldiv_op2_i,
    input wire muldiv_op_mul_i,
    input wire muldiv_op_mulh_i,
    input wire muldiv_op_mulhsu_i,
    input wire muldiv_op_mulhu_i,
    input wire muldiv_op_div_i,
    input wire muldiv_op_divu_i,
    input wire muldiv_op_rem_i,
    input wire muldiv_op_remu_i,

    output wire[31:0] muldiv_reg_wdata_o,
    output wire muldiv_reg_we_o,
    output wire muldiv_stall_o

    );

    // 除法操作
    wire op_div = muldiv_op_div_i | muldiv_op_divu_i | muldiv_op_rem_i | muldiv_op_remu_i;
    wire div_start = op_div & (!div_ready);
    wire[3:0] div_op = {muldiv_op_div_i, muldiv_op_divu_i, muldiv_op_rem_i, muldiv_op_remu_i};
    wire[31:0] div_result;
    wire div_ready;

    divider u_divider(
        .clk(clk),
        .rst_n(rst_n),
        .dividend_i(muldiv_op1_i),
        .divisor_i(muldiv_op2_i),
        .start_i(div_start),
        .op_i(div_op),
        .result_o(div_result),
        .ready_o(div_ready)
    );

    // Blocking multiply: capture operands, register four parallel partial
    // products, then combine into the existing EX/MEM result boundary.
    // No abs/negate chain surrounds the multiplier. Signed high halfwords
    // implement MULH/MULHSU directly; unsigned low halfwords serve all modes.
    wire op_mul = muldiv_op_mul_i | muldiv_op_mulh_i | muldiv_op_mulhsu_i | muldiv_op_mulhu_i;
    reg[1:0] mul_valid;
    wire mul_start = op_mul && !(|mul_valid);
    wire mul_ready = op_mul && mul_valid[1];
    reg mul_high;
    reg signed[16:0] a_low,a_high,b_low,b_high;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) mul_valid<=0;
        else if (!op_mul) mul_valid<=0; // EX flush/cancel or saved completion
        else mul_valid<={mul_valid[0],mul_start};
    end
    // Data need not reset: only mul_valid authorizes consumption. This simple
    // clock/enable structure permits ADS to pack data FFs into APM registers.
    always @(posedge clk) begin
        if (mul_start) begin
            a_low<=$signed({1'b0,muldiv_op1_i[15:0]});
            b_low<=$signed({1'b0,muldiv_op2_i[15:0]});
            a_high<=$signed({(muldiv_op_mulh_i || muldiv_op_mulhsu_i) && muldiv_op1_i[31],muldiv_op1_i[31:16]});
            b_high<=$signed({muldiv_op_mulh_i && muldiv_op2_i[31],muldiv_op2_i[31:16]});
            mul_high<=!muldiv_op_mul_i;
        end
    end
    wire signed[33:0] ll /* synthesis syn_dspstyle = "block_mult" */;
    wire signed[33:0] lh /* synthesis syn_dspstyle = "block_mult" */;
    wire signed[33:0] hl /* synthesis syn_dspstyle = "block_mult" */;
    wire signed[33:0] hh /* synthesis syn_dspstyle = "block_mult" */;
    assign ll=a_low*b_low;
    assign lh=a_low*b_high;
    assign hl=a_high*b_low;
    assign hh=a_high*b_high;
    reg signed[33:0] ll_q,lh_q,hl_q,hh_q;
    always @(posedge clk) begin
        ll_q<=ll; lh_q<=lh; hl_q<=hl; hh_q<=hh;
    end
    // A*B = ll + ((lh+hl)<<16) + (hh<<32), modulo 2^64.
    // Sign extension keeps cross-term carries correct for negative operands.
    wire signed[34:0] middle=$signed({lh_q[33],lh_q}) +
        $signed({hl_q[33],hl_q}) + $signed({19'b0,ll_q[31:16]});
    wire[31:0] low_product={middle[15:0],ll_q[15:0]};
    wire[31:0] high_product=hh_q[31:0]+{{13{middle[34]}},middle[34:16]};
    wire[31:0] mul_op_res=mul_high ? high_product : low_product;

    // 运算结果
    // Select the divider explicitly; stale multiplication data are invalid.
    assign muldiv_reg_wdata_o = div_ready ? div_result : mul_op_res;
    assign muldiv_reg_we_o = div_ready | mul_ready;
    assign muldiv_stall_o = div_start | (op_mul && !mul_ready);

endmodule
