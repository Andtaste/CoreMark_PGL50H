 /*                                                                      
 Copyright 2019 Blue Liang, liangkangnan@163.com
                                                                         
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

// Five-stage, in-order, single-issue RV32IM/Zicsr implementation.
// IF uses synchronous RAM and a skid queue. ID reads the register file.
// EX computes/forwards, MEM owns exactly one data transaction, WB commits.
// PDS 2022.2 can recurse incorrectly while inferring an FSM through pipeline
// payload/valid feedback. Keep the explicitly coded control bits here; this
// attribute changes synthesis inference only, not pipeline behavior.
(* syn_state_machine = 0 *)
module tinyriscv_core(
    input wire clk, rst_n,
    output wire[31:0] dbus_addr_o,
    input wire[31:0] dbus_data_i,
    output wire[31:0] dbus_data_o,
    output wire[3:0] dbus_sel_o,
    output wire dbus_we_o, dbus_req_valid_o,
    input wire dbus_req_ready_i, dbus_rsp_valid_i,
    output wire dbus_rsp_ready_o,
    output wire[31:0] ibus_addr_o,
    input wire[31:0] ibus_data_i,
    output wire[31:0] ibus_data_o,
    output wire[3:0] ibus_sel_o,
    output wire ibus_we_o, ibus_req_valid_o,
    input wire ibus_req_ready_i, ibus_rsp_valid_i,
    output wire ibus_rsp_ready_o,
    input wire jtag_halt_i,
    input wire[`INT_WIDTH-1:0] int_i
);
    wire[31:0] id_inst, id_pc;
    wire[1:0] id_fetch_fault;
    wire id_valid, id_fire, frontend_flush, frontend_stop;
    wire[31:0] frontend_target;
    assign ibus_data_o=0;
    assign ibus_sel_o=4'b1111;
    assign ibus_we_o=0;
    ifu_p5 u_ifu(
        .clk(clk),.rst_n(rst_n),.flush_i(frontend_flush),
        .flush_addr_i(frontend_target),.stop_i(frontend_stop),
        .inst_o(id_inst),.pc_o(id_pc),.fault_o(id_fetch_fault),
        .valid_o(id_valid),.ready_i(id_fire),
        .addr_o(ibus_addr_o),.req_valid_o(ibus_req_valid_o),
        .req_ready_i(ibus_req_ready_i),.rdata_i(ibus_data_i),
        .rsp_valid_i(ibus_rsp_valid_i),.rsp_ready_o(ibus_rsp_ready_o)
    );

    // Decode reuses the existing immediate/register-use decoder. Execution
    // independently validates the opcode so invalid encodings cannot write.
    wire[4:0] id_rs1,id_rs2,id_rd;
    wire id_rd_we;
    wire[31:0] id_src1,id_src2,id_imm;
    wire[`DECINFO_WIDTH-1:0] id_info;
    idu u_idu(
        .clk(clk),.rst_n(rst_n),.inst_i(id_inst),.inst_addr_i(id_pc),
        .rs1_rdata_i(id_src1),.rs2_rdata_i(id_src2),
        .rs1_raddr_o(id_rs1),.rs2_raddr_o(id_rs2),
        .rd_waddr_o(id_rd),.rd_we_o(id_rd_we),
        .dec_imm_o(id_imm),.dec_info_bus_o(id_info),
        .inst_o(),.dec_pc_o(),.rs1_rdata_o(),.rs2_rdata_o(),.stall_o()
    );

    reg ex_valid;
    reg[31:0] ex_inst,ex_pc,ex_imm,ex_src1,ex_src2;
    reg[4:0] ex_rs1,ex_rs2,ex_rd;
    reg ex_rd_we;
    reg[1:0] ex_fetch_fault;
    reg[`DECINFO_WIDTH-1:0] ex_info;
    reg ex_md_done;
    reg[31:0] ex_md_saved;

    reg mem_valid,mem_sent,mem_load,mem_store,mem_rd_we,mem_serial;
    reg mem_exception,mem_csr_we,mem_mret;
    reg[4:0] mem_rd;
    reg[2:0] mem_funct3;
    reg[31:0] mem_pc,mem_next_pc,mem_result,mem_addr,mem_store_data;
    reg[31:0] mem_cause,mem_csr_data;
    reg[11:0] mem_csr_addr;

    reg wb_valid,wb_rd_we,wb_exception,wb_csr_we,wb_mret,wb_serial;
    reg[4:0] wb_rd;
    reg[31:0] wb_pc,wb_next_pc,wb_result,wb_cause,wb_csr_data;
    reg[11:0] wb_csr_addr;
    wire wb_commit=wb_valid && !wb_exception;
    wire wb_gpr_we=wb_commit && wb_rd_we && wb_rd!=0;
    gpr_reg u_gpr_reg(
        .clk(clk),.rst_n(rst_n),.we_i(wb_gpr_we),
        .waddr_i(wb_rd),.wdata_i(wb_result),
        .raddr1_i(id_rs1),.rdata1_o(id_src1),
        .raddr2_i(id_rs2),.rdata2_o(id_src2)
    );

    // CSR instructions are serialized, with writes only at WB. Interrupts
    // stop admission at ID and wait for all older instructions to retire.
    wire[31:0] csr_read,csr_mtvec,csr_mepc,csr_mstatus,csr_mie;
    reg[1:0] trap_state;
    reg[31:0] trap_epc,trap_cause,trap_status,trap_target;
    reg[31:0] architectural_pc;
    wire irq_pending=(|int_i) && csr_mstatus[3] && csr_mie[7];
    wire irq_take=irq_pending && !ex_valid && !mem_valid && !wb_valid && trap_state==0;
    wire trap_start=(wb_valid && wb_exception && trap_state==0) || irq_take;
    wire trap_finish=trap_state==3;
    wire return_from_trap=wb_commit && wb_mret;
    wire hard_flush=trap_start || trap_state!=0 || return_from_trap;
    wire trap_csr_we=trap_state!=0 || return_from_trap;
    wire[31:0] trap_csr_addr=trap_state==1 ? {20'b0,`CSR_MEPC} :
        trap_state==2 ? {20'b0,`CSR_MCAUSE} : {20'b0,`CSR_MSTATUS};
    wire[31:0] mret_status=(csr_mstatus & ~32'h00001888) |
        32'h00001880 | (csr_mstatus[7] ? 32'h8 : 32'h0);
    wire[31:0] trap_csr_data=return_from_trap ? mret_status :
        trap_state==1 ? trap_epc : trap_state==2 ? trap_cause : trap_status;
    wire[6:0] stat_events;
    csr_reg u_csr_reg(
        .clk(clk),.rst_n(rst_n),.stat_events_i(stat_events),
        .exu_we_i(wb_commit && wb_csr_we),
        .exu_waddr_i({20'b0,wb_csr_addr}),.exu_wdata_i(wb_csr_data),
        .exu_raddr_i({20'b0,ex_inst[31:20]}),.exu_rdata_o(csr_read),
        .clint_we_i(trap_csr_we),.clint_waddr_i(trap_csr_addr),
        .clint_wdata_i(trap_csr_data),.mtvec_o(csr_mtvec),
        .mepc_o(csr_mepc),.mstatus_o(csr_mstatus),.mie_o(csr_mie)
    );
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            trap_state<=0; trap_epc<=0; trap_cause<=0;
            trap_status<=0; trap_target<=0; architectural_pc<=`CPU_RESET_ADDR;
        end else begin
            if (wb_commit) architectural_pc<=wb_next_pc;
            if (trap_start) begin
                trap_state<=1;
                trap_epc<=irq_take ? architectural_pc : wb_pc;
                trap_cause<=irq_take ? 32'h80000007 : wb_cause;
                trap_status<=(csr_mstatus & ~32'h00001888) | 32'h1800 |
                    (csr_mstatus[3] ? 32'h80 : 32'h0);
                trap_target<={csr_mtvec[31:2],2'b0} +
                    ((irq_take && csr_mtvec[1:0]==1) ? 32'd28 : 32'd0);
            end else begin
                case (trap_state)
                    1: trap_state<=2;
                    2: trap_state<=3;
                    3: trap_state<=0;
                    default: trap_state<=0;
                endcase
            end
            if (trap_finish) begin trap_state<=0; architectural_pc<=trap_target; end
            if (return_from_trap) architectural_pc<={csr_mepc[31:2],2'b0};
        end
    end

    // MEM issues once, then holds metadata until the tagged response arrives.
    // This conservative first implementation does not speculate MMIO reads
    // or acknowledge stores before their actual device acceptance.
    wire mem_access=mem_load || mem_store;
    wire mem_complete=mem_valid && (!mem_access || (mem_sent && dbus_rsp_valid_i));
    wire mem_ready=!mem_valid || mem_complete;
    assign dbus_addr_o=mem_addr;
    assign dbus_data_o=mem_store_data << {mem_addr[1:0],3'b000};
    assign dbus_sel_o=mem_funct3==0 ? (4'b0001 << mem_addr[1:0]) :
        mem_funct3==1 ? (4'b0011 << mem_addr[1:0]) : 4'b1111;
    assign dbus_req_valid_o=mem_valid && mem_access && !mem_sent && !hard_flush;
    assign dbus_we_o=mem_store && dbus_req_valid_o;
    assign dbus_rsp_ready_o=1'b1;
    wire[31:0] load_shifted=dbus_data_i >> {mem_addr[1:0],3'b000};
    wire[31:0] load_value=mem_funct3==0 ? {{24{load_shifted[7]}},load_shifted[7:0]} :
        mem_funct3==1 ? {{16{load_shifted[15]}},load_shifted[15:0]} :
        mem_funct3==4 ? {24'b0,load_shifted[7:0]} :
        mem_funct3==5 ? {16'b0,load_shifted[15:0]} : dbus_data_i;
    wire[31:0] mem_value=mem_load ? load_value : mem_result;

    // Closest older producer wins. Loads are forwarded from WB, keeping the
    // RAM output -> ALU path out of the EX critical path in this baseline.
    wire mem_match1=mem_valid && mem_rd_we && mem_rd!=0 && mem_rd==ex_rs1;
    wire mem_match2=mem_valid && mem_rd_we && mem_rd!=0 && mem_rd==ex_rs2;
    wire wb_match1=wb_gpr_we && wb_rd==ex_rs1;
    wire wb_match2=wb_gpr_we && wb_rd==ex_rs2;
    wire[31:0] src1=ex_rs1==0 ? 32'b0 :
        (mem_match1 && !mem_load) ? mem_result : wb_match1 ? wb_result : ex_src1;
    wire[31:0] src2=ex_rs2==0 ? 32'b0 :
        (mem_match2 && !mem_load) ? mem_result : wb_match2 ? wb_result : ex_src2;
    wire ex_load_dependency=mem_load && (mem_match1 || mem_match2);
    wire[6:0] opcode=ex_inst[6:0];
    wire[2:0] funct3=ex_inst[14:12];
    wire[6:0] funct7=ex_inst[31:25];
    wire ex_is_md=opcode==7'b0110011 && funct7==1;
    wire ex_serial=opcode==7'b1110011 || opcode==7'b0001111 || ex_fetch_fault!=0;
    wire id_serial=id_inst[6:0]==7'b1110011 || id_inst[6:0]==7'b0001111 || id_fetch_fault!=0;
    wire[31:0] md_value;
    wire md_ready,md_stall;
    wire md_enable=ex_valid && ex_is_md && !ex_md_done && !hard_flush;
    exu_muldiv u_exu_muldiv(
        .clk(clk),.rst_n(rst_n),.muldiv_op1_i(src1),.muldiv_op2_i(src2),
        .muldiv_op_mul_i(md_enable && funct3==0),
        .muldiv_op_mulh_i(md_enable && funct3==1),
        .muldiv_op_mulhsu_i(md_enable && funct3==2),
        .muldiv_op_mulhu_i(md_enable && funct3==3),
        .muldiv_op_div_i(md_enable && funct3==4),
        .muldiv_op_divu_i(md_enable && funct3==5),
        .muldiv_op_rem_i(md_enable && funct3==6),
        .muldiv_op_remu_i(md_enable && funct3==7),
        .muldiv_reg_wdata_o(md_value),.muldiv_reg_we_o(md_ready),.muldiv_stall_o(md_stall)
    );

    function csr_known;
        input[11:0] a;
        begin
            case(a)
                `CSR_CYCLE,`CSR_CYCLEH,`CSR_MTVEC,`CSR_MCAUSE,`CSR_MEPC,
                `CSR_MIE,`CSR_MSTATUS,`CSR_MSCRATCH,
                12'h7c0,12'h7c1,12'h7c2,12'h7c3,12'h7c4,12'h7c5,
                12'h7c6,12'h7c7,12'h7c8,12'h7cf: csr_known=1;
                default: csr_known=0;
            endcase
        end
    endfunction
    function csr_writable;
        input[11:0] a;
        begin
            case(a)
                `CSR_MTVEC,`CSR_MCAUSE,`CSR_MEPC,`CSR_MIE,`CSR_MSTATUS,
                `CSR_MSCRATCH,12'h7c0: csr_writable=1;
                default: csr_writable=0;
            endcase
        end
    endfunction

    reg[31:0] ex_result,ex_address,ex_next_pc,ex_cause,ex_csr_data;
    reg ex_load,ex_store,ex_redirect,ex_exception,ex_csr_we,ex_mret,ex_illegal;
    reg branch_condition;
    wire[31:0] rhs=opcode==7'b0010011 ? ex_imm : src2;
    wire lt_u=src1<rhs;
    wire lt_s=(src1[31]^rhs[31]) ? src1[31] : lt_u;
    // Keep the arithmetic shift in a signed expression, outside an unsigned
    // conditional expression (which would otherwise zero-fill negative SRA).
    wire signed[32:0] right_operand={ex_inst[30] && src1[31],src1};
    wire signed[32:0] right_shifted=right_operand >>> rhs[4:0];
    wire[31:0] csr_operand=funct3[2] ? {27'b0,ex_inst[19:15]} : src1;
    always @(*) begin
        ex_result=0; ex_address=src1+ex_imm; ex_next_pc=ex_pc+32'd4;
        ex_load=0; ex_store=0; ex_redirect=0; ex_exception=0;
        ex_cause=0; ex_csr_we=0; ex_csr_data=0; ex_mret=0;
        ex_illegal=0; branch_condition=0;
        case(opcode)
            7'b0110111: ex_result={ex_inst[31:12],12'b0};
            7'b0010111: ex_result=ex_pc+ex_imm;
            7'b1101111: begin
                ex_result=ex_pc+32'd4; ex_next_pc=ex_pc+ex_imm; ex_redirect=1;
            end
            7'b1100111: begin
                ex_result=ex_pc+32'd4; ex_next_pc=(src1+ex_imm)&32'hfffffffe;
                ex_redirect=1; ex_illegal=funct3!=0;
            end
            7'b1100011: begin
                case(funct3)
                    0: branch_condition=src1==src2;
                    1: branch_condition=src1!=src2;
                    4: branch_condition=$signed(src1)<$signed(src2);
                    5: branch_condition=$signed(src1)>=$signed(src2);
                    6: branch_condition=src1<src2;
                    7: branch_condition=src1>=src2;
                    default: ex_illegal=1;
                endcase
                if (branch_condition) begin ex_redirect=1; ex_next_pc=ex_pc+ex_imm; end
            end
            7'b0010011,7'b0110011: begin
                if (ex_is_md) ex_result=ex_md_done ? ex_md_saved : md_value;
                else begin
                    case(funct3)
                        0: ex_result=src1 + (opcode==7'b0110011 && funct7==7'h20 ? (~rhs+32'd1) : rhs);
                        1: ex_result=src1 << rhs[4:0];
                        2: ex_result={31'b0,lt_s};
                        3: ex_result={31'b0,lt_u};
                        4: ex_result=src1^rhs;
                        5: ex_result=right_shifted[31:0];
                        6: ex_result=src1|rhs;
                        7: ex_result=src1&rhs;
                    endcase
                    if (opcode==7'b0110011)
                        ex_illegal=funct7!=0 && !(funct7==7'h20 && (funct3==0 || funct3==5));
                    else if (funct3==1) ex_illegal=funct7!=0;
                    else if (funct3==5) ex_illegal=funct7!=0 && funct7!=7'h20;
                end
            end
            7'b0000011,7'b0100011: begin
                ex_load=opcode==7'b0000011; ex_store=opcode==7'b0100011;
                ex_illegal=ex_store ? funct3>2 :
                    !(funct3==0 || funct3==1 || funct3==2 || funct3==4 || funct3==5);
                if ((funct3==2 && |ex_address[1:0]) ||
                    ((funct3==1 || funct3==5) && ex_address[0])) begin
                    ex_exception=1; ex_cause=ex_store ? 32'd6 : 32'd4;
                end else if (ex_address[31:28]>4) begin
                    ex_exception=1; ex_cause=ex_store ? 32'd7 : 32'd5;
                end
            end
            7'b0001111: begin
                ex_illegal=funct3!=0 && funct3!=1;
                ex_redirect=1;
            end
            7'b1110011: begin
                if (funct3==0) begin
                    case(ex_inst)
                        32'h00000073: begin ex_exception=1; ex_cause=11; end
                        32'h00100073: begin ex_exception=1; ex_cause=3; end
                        32'h30200073: ex_mret=1;
                        32'h10500073: ; // WFI may legally act as a NOP.
                        default: ex_illegal=1;
                    endcase
                end else begin
                    ex_result=csr_read;
                    ex_illegal=funct3==4 || !csr_known(ex_inst[31:20]);
                    ex_csr_we=funct3[1:0]==1 || ex_inst[19:15]!=0;
                    case(funct3[1:0])
                        1: ex_csr_data=csr_operand;
                        2: ex_csr_data=csr_read|csr_operand;
                        3: ex_csr_data=csr_read&~csr_operand;
                        default: ex_csr_data=csr_read;
                    endcase
                    if (ex_csr_we && !csr_writable(ex_inst[31:20])) ex_illegal=1;
                end
            end
            default: ex_illegal=1;
        endcase
        if (ex_redirect && |ex_next_pc[1:0]) begin ex_exception=1; ex_cause=0; end
        if (ex_illegal) begin ex_exception=1; ex_cause=2; end
        if (ex_fetch_fault!=0) begin
            ex_exception=1; ex_cause=ex_fetch_fault==1 ? 32'd0 : 32'd1;
        end
        if (ex_exception) begin ex_load=0; ex_store=0; ex_csr_we=0; ex_mret=0; ex_redirect=0; end
    end

    wire ex_finished=!ex_is_md || ex_md_done || md_ready || ex_exception;
    wire ex_fire=ex_valid && mem_ready && ex_finished && !ex_load_dependency && !hard_flush;
    wire ex_ready=!ex_valid || ex_fire;
    wire id_dep_ex_load=ex_valid && ex_load && ex_rd_we && ex_rd!=0 &&
        (ex_rd==id_rs1 || ex_rd==id_rs2);
    wire id_dep_mem_load=mem_valid && mem_load && mem_rd_we && mem_rd!=0 &&
        (mem_rd==id_rs1 || mem_rd==id_rs2);
    wire serial_wait=(id_serial && (ex_valid || mem_valid || wb_valid)) ||
        (ex_valid && ex_serial) || (mem_valid && mem_serial) || (wb_valid && wb_serial);
    wire fault_inflight=(ex_valid && ex_exception) ||
        (mem_valid && mem_exception) || (wb_valid && wb_exception);
    wire ex_flush=ex_fire && (ex_redirect || ex_exception);
    assign id_fire=id_valid && ex_ready && !id_dep_ex_load && !id_dep_mem_load &&
        !serial_wait && !irq_pending && !hard_flush && !ex_flush && !fault_inflight;
    assign frontend_stop=jtag_halt_i || irq_pending || trap_state!=0 || fault_inflight;
    assign frontend_flush=ex_flush || trap_start || trap_finish || return_from_trap;
    assign frontend_target=return_from_trap ? {csr_mepc[31:2],2'b0} :
        trap_finish ? trap_target : trap_start ? {csr_mtvec[31:2],2'b0} : ex_next_pc;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ex_valid<=0; ex_inst<=0; ex_pc<=0; ex_imm<=0;
            ex_src1<=0; ex_src2<=0; ex_rs1<=0; ex_rs2<=0; ex_rd<=0;
            ex_rd_we<=0; ex_fetch_fault<=0; ex_info<=0;
            ex_md_done<=0; ex_md_saved<=0;
        end else if (hard_flush) begin ex_valid<=0; ex_md_done<=0; end
        else if (id_fire) begin
            ex_valid<=1; ex_inst<=id_inst; ex_pc<=id_pc; ex_imm<=id_imm;
            ex_src1<=id_src1; ex_src2<=id_src2; ex_rs1<=id_rs1; ex_rs2<=id_rs2;
            ex_rd<=id_rd; ex_rd_we<=id_rd_we; ex_fetch_fault<=id_fetch_fault;
            ex_info<=id_info; ex_md_done<=0;
        end else begin
            if (ex_fire) begin ex_valid<=0; ex_md_done<=0; end
            else if (ex_valid) begin
                // An older producer can retire while EX is held by MEM.
                // Save its forwarded values before its WB valid disappears.
                ex_src1<=src1; ex_src2<=src2;
                if (ex_is_md && md_ready && !ex_md_done) begin
                    ex_md_done<=1; ex_md_saved<=md_value;
                end
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            mem_valid<=0; mem_sent<=0; mem_load<=0; mem_store<=0;
            mem_rd_we<=0; mem_serial<=0; mem_exception<=0; mem_csr_we<=0; mem_mret<=0;
            mem_rd<=0; mem_funct3<=0; mem_pc<=0; mem_next_pc<=0;
            mem_result<=0; mem_addr<=0; mem_store_data<=0;
            mem_cause<=0; mem_csr_data<=0; mem_csr_addr<=0;
        end else if (hard_flush) begin mem_valid<=0; mem_sent<=0; end
        else if (ex_fire) begin
            mem_valid<=1; mem_sent<=0; mem_load<=ex_load; mem_store<=ex_store;
            mem_rd_we<=ex_rd_we && !ex_exception; mem_rd<=ex_rd;
            mem_funct3<=funct3; mem_pc<=ex_pc; mem_next_pc<=ex_next_pc;
            mem_result<=ex_result; mem_addr<=ex_address; mem_store_data<=src2;
            mem_exception<=ex_exception; mem_cause<=ex_cause;
            mem_csr_we<=ex_csr_we; mem_csr_addr<=ex_inst[31:20]; mem_csr_data<=ex_csr_data;
            mem_mret<=ex_mret; mem_serial<=ex_serial;
        end else begin
            if (dbus_req_valid_o && dbus_req_ready_i) mem_sent<=1;
            if (mem_complete) begin mem_valid<=0; mem_sent<=0; end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wb_valid<=0; wb_rd_we<=0; wb_exception<=0; wb_csr_we<=0;
            wb_mret<=0; wb_serial<=0; wb_rd<=0; wb_pc<=0;
            wb_next_pc<=0; wb_result<=0; wb_cause<=0; wb_csr_data<=0; wb_csr_addr<=0;
        end else if (hard_flush) wb_valid<=0;
        else begin
            wb_valid<=mem_complete;
            if (mem_complete) begin
                wb_rd_we<=mem_rd_we; wb_rd<=mem_rd; wb_result<=mem_value;
                wb_pc<=mem_pc; wb_next_pc<=mem_next_pc;
                wb_exception<=mem_exception; wb_cause<=mem_cause;
                wb_csr_we<=mem_csr_we; wb_csr_addr<=mem_csr_addr; wb_csr_data<=mem_csr_data;
                wb_mret<=mem_mret; wb_serial<=mem_serial;
            end
        end
    end
    // Preserve the v1 CSR layout. Wait events now refer to their owning stage.
    wire ex_bjp=opcode==7'b1100011 || opcode==7'b1101111 || opcode==7'b1100111;
    assign stat_events={ex_fire && ex_bjp && !ex_exception,
        ex_fire && ex_bjp && ex_redirect && !ex_exception,
        ex_valid && ex_is_md && !ex_finished,
        mem_valid && mem_access && !mem_complete,
        !id_valid && ex_ready && !frontend_stop && !frontend_flush,
        ibus_req_valid_o && !ibus_req_ready_i,1'b1};
    // Stable observation aliases used by the existing functional TB.
    wire[31:0] ie_inst_o=ex_inst;
    wire[31:0] ie_dec_pc_o=ex_pc;
    wire ex_hold_flag_o=!ex_fire;
endmodule
