`timescale 1ns/1ps
module cpu_bus_soc_tb;
    parameter PARALLEL_ACCESS = 1;
    reg clk=0;
    always #10 clk=~clk;
    reg rst_n=0;
    wire[1:0] gpio;
    tinyriscv_soc_top #(.PARALLEL_ACCESS(PARALLEL_ACCESS)) dut(
        .clk(clk), .rst_ext_i(rst_n), .halted_ind(),
        .uart_tx_pin(), .uart_rx_pin(1'b1), .gpio(gpio),
        .jtag_TCK(1'b0), .jtag_TMS(1'b1), .jtag_TDI(1'b0), .jtag_TDO()
    );
    reg[2047:0] image;
    reg[31:0] finish_pc;
    integer i, cycles=0, parallel_grants=0, limit=250000, coremark=0, progress=100000;
    initial begin
        if (!$value$plusargs("image=%s", image)) $fatal(1, "Missing image");
        i=$value$plusargs("limit=%d", limit);
        i=$value$plusargs("coremark=%d", coremark);
        i=$value$plusargs("progress=%d", progress);
        if (coremark && !$value$plusargs("finish_pc=%h", finish_pc))
            $fatal(1, "CoreMark requires its linked exit-loop address");
        for (i=0;i<16384;i=i+1) dut.u_rom.rom111.memory[i]=0;
        for (i=0;i<8192;i=i+1) dut.u_ram.ram222.memory[i]=0;
        $readmemh(image, dut.u_rom.rom111.memory);
        // Only accelerate serial transmission in the CoreMark smoke run.
        // CPU, RAM and bus timings remain unchanged.
        if (coremark) force dut.uart_0.uart_baud=32'd1;
        #80 rst_n=1;
    end
    always @(posedge clk) begin
        if (dut.rst_n) begin
            cycles=cycles+1;
            if (coremark && progress>0 && cycles%progress==0) begin
                $display("\nSIM_PROGRESS cycles=%0d pc=%08x",cycles,dut.u_tinyriscv_core.u_ifu.pc);
                $fflush();
            end
            if (dut.m0_req_vld_i && dut.m0_req_rdy_o &&
                dut.m1_req_vld_i && dut.m1_req_rdy_o)
                parallel_grants=parallel_grants+1;
            if (cycles>limit) $fatal(1, "TEST_TIMEOUT cycles=%0d pc=%08x", cycles, dut.u_tinyriscv_core.u_ifu.pc);
        end
        if (coremark && dut.uart_0.tx_start)
            $write("%c", dut.s3_data_o[7:0]);
    end
    initial begin
        wait(dut.rst_n===1'b1);
        if (coremark) begin
            // C may legitimately use x26/x27. Detect the executed exit loop,
            // not a transient C register value or a speculative fetched PC.
            wait(dut.u_tinyriscv_core.ie_dec_pc_o===finish_pc &&
                 dut.u_tinyriscv_core.ie_inst_o===32'h0000006f &&
                 dut.u_tinyriscv_core.ex_hold_flag_o===1'b0);
        end else begin
            wait(dut.u_tinyriscv_core.u_gpr_reg.regs[26]===32'd1);
        end
        // The legacy PASS macro writes x26 first, then x27 on the next
        // instruction. Allow the pipeline to finish that status update.
        #100;
        if (!coremark && dut.u_tinyriscv_core.u_gpr_reg.regs[27]!==32'd1)
            $fatal(1, "TEST_FAIL testnum=%0d", dut.u_tinyriscv_core.u_gpr_reg.regs[3]);
        $display("\nTEST_PASS cycles=%0d mode=%0d parallel_grants=%0d", cycles, PARALLEL_ACCESS, parallel_grants);
        $finish;
    end
endmodule
