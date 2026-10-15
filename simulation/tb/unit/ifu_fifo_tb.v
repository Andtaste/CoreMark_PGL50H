`timescale 1ns/1ps
// Focused frontend protocol check, independent of instruction execution.
module ifu_fifo_tb;
    reg clk=0, rst_n=0;
    always #5 clk=~clk;
    reg flush=0, stop=0, ready=0, req_ready=0, rsp_valid=0;
    reg[31:0] target=0, rdata=0;
    wire[31:0] inst,pc,addr;
    wire[1:0] fault;
    wire valid,req,rsp_ready;
    ifu_p5 dut(.clk(clk),.rst_n(rst_n),.flush_i(flush),
        .flush_addr_i(target),.stop_i(stop),.inst_o(inst),.pc_o(pc),
        .fault_o(fault),.valid_o(valid),.ready_i(ready),.addr_o(addr),
        .req_valid_o(req),.req_ready_i(req_ready),.rdata_i(rdata),
        .rsp_valid_i(rsp_valid),.rsp_ready_o(rsp_ready));
    integer cycle=0,delay_left=0,pops=0,full=0,held_flush=0;
    integer pending_flush=0,response_flush=0,turnover=0,faults=0;
    reg busy=0,stalled=0;
    reg[31:0] payload=0,held_addr=0,expected=0;
    reg[1:0] expected_fault;
    always @(negedge clk) begin
        if(!rst_n) begin
            req_ready=0; rsp_valid=0;
        end else begin
            cycle=cycle+1;
            ready=!(cycle>=10 && cycle<75) && cycle%5!=0;
            stop=cycle>=180 && cycle<200;
            req_ready=(!busy || rsp_valid) && cycle%4!=0 &&
                !(cycle>=76 && cycle<=85);
            flush=0;
            // Consecutive redirects and redirect coincident with old response
            // or held command are selected from actual transaction state.
            if ((cycle>78 && cycle<85 && req && !req_ready) ||
                (cycle>90 && cycle<120 && rsp_valid) ||
                cycle==140 || cycle==141 || cycle==240 || cycle==300)
                flush=1;
            target=cycle==240 ? 32'h30000000 :
                cycle==300 ? 32'h00000402 : 32'h00000800+cycle*32;
        end
    end
    always @(posedge clk) begin
        if(rst_n) begin
            if(stalled && (!req || addr!==held_addr))
                $fatal(1,"withdrawn/changed held command cycle=%0d",cycle);
            stalled=req && !req_ready;
            held_addr=addr;
            if(dut.reserved>4 || dut.count>4)
                $fatal(1,"FIFO reservation overflow");
            if(dut.count==4) full=full+1;
            if(flush) begin
                expected=target;
                if(req && !req_ready) held_flush=held_flush+1;
                if(dut.pending) pending_flush=pending_flush+1;
                if(rsp_valid) response_flush=response_flush+1;
            end else if(valid && ready) begin
                expected_fault=|expected[1:0] ? 1 : expected[31:28]>1 ? 2 : 0;
                if(pc!==expected || fault!==expected_fault)
                    $fatal(1,"PC/fault expected=%h/%0d actual=%h/%0d",expected,expected_fault,pc,fault);
                if(fault==0 && inst!==(pc^32'h5a5a1234))
                    $fatal(1,"instruction/PC mismatch");
                if(fault!=0) faults=faults+1;
                expected=expected+4;
                pops=pops+1;
            end
            if(req && req_ready && rsp_valid) turnover=turnover+1;
            if(rsp_valid) begin rsp_valid<=0; busy<=0; end
            if(delay_left>0) begin
                delay_left<=delay_left-1;
                if(delay_left==1) begin rsp_valid<=1; rdata<=payload; end
            end
            if(req && req_ready) begin
                if(busy && !rsp_valid) $fatal(1,"multiple outstanding requests");
                busy<=1; payload<=addr^32'h5a5a1234;
                delay_left<=cycle<180 ? 1 : 2+cycle%4;
            end
            if(cycle==400) begin
                if(!full || !held_flush || !pending_flush || !response_flush ||
                   !turnover || faults<2 || pops<20)
                    $fatal(1,"coverage full=%0d held=%0d pending=%0d response=%0d turnover=%0d faults=%0d pops=%0d",
                        full,held_flush,pending_flush,response_flush,turnover,faults,pops);
                $display("TEST_PASS IFU_FIFO pops=%0d full=%0d held_flush=%0d pending_flush=%0d response_flush=%0d turnover=%0d faults=%0d",
                    pops,full,held_flush,pending_flush,response_flush,turnover,faults);
                $finish;
            end
        end
    end
    initial begin
        repeat(3) @(negedge clk);
        rst_n=1;
    end
endmodule
