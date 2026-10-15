`timescale 1ns/1ps
module rib_owner_tb;
    reg clk=0,rst_n=0;
    always #5 clk=~clk;
    reg[31:0] a0=0,a1=0;
    reg q0=0,q1=0,r0=0,r1=1,we1=0;
    wire g0,g1,v0,v1;
    wire[31:0] d0,d1,sa0,sa1;
    wire sq0,sq1,sr0,sr1,sw0,sw1;
    reg sv0=0,sv1=0;
    reg[31:0] sd0=0,sd1=0;
    integer writes=0;
    wire sg0=!sv0 || sr0;
    wire sg1=!sv1 || sr1;
        local_ram_bus dut(
        .clk(clk),.rst_n(rst_n),
        .m0_addr_i(a0),.m0_data_i(32'b0),.m0_sel_i(4'hf),.m0_we_i(1'b0),
        .m0_req_vld_i(q0),.m0_rsp_rdy_i(r0),.m0_req_rdy_o(g0),.m0_rsp_vld_o(v0),.m0_data_o(d0),
        .m1_addr_i(a1),.m1_data_i(32'h12345678),.m1_sel_i(4'hf),.m1_we_i(we1),
        .m1_req_vld_i(q1),.m1_rsp_rdy_i(r1),.m1_req_rdy_o(g1),.m1_rsp_vld_o(v1),.m1_data_o(d1),
        .m2_addr_i(32'b0),.m2_data_i(32'b0),.m2_sel_i(4'b0),.m2_we_i(1'b0),
        .m2_req_vld_i(1'b0),.m2_rsp_rdy_i(1'b1),
        .s0_addr_o(sa0),.s0_req_vld_o(sq0),.s0_rsp_rdy_o(sr0),.s0_we_o(sw0),
        .s0_data_i(sd0),.s0_req_rdy_i(sg0),.s0_rsp_vld_i(sv0),
        .s1_addr_o(sa1),.s1_req_vld_o(sq1),.s1_rsp_rdy_o(sr1),.s1_we_o(sw1),
        .s1_data_i(sd1),.s1_req_rdy_i(sg1),.s1_rsp_vld_i(sv1),
        .s2_data_i(32'b0),.s2_req_rdy_i(1'b0),.s2_rsp_vld_i(1'b0),
        .s3_data_i(32'b0),.s3_req_rdy_i(1'b0),.s3_rsp_vld_i(1'b0),
        .s4_data_i(32'b0),.s4_req_rdy_i(1'b0),.s4_rsp_vld_i(1'b0)
        );
    always @(posedge clk) begin
        if (!rst_n) begin sv0<=0; sv1<=0; writes<=0; end
        else begin
            if (sg0) begin
                sv0<=sq0;
                if(sq0) sd0<=32'haa000000|sa0;
            end
            if (sg1) begin
                sv1<=sq1;
                if(sq1) sd1<=32'hbb000000|sa1;
            end
            if (sq0 && sg0 && sw0) writes<=writes+1;
        end
    end
    initial begin
        repeat(2) @(negedge clk);
        rst_n=1; q0=1; a0=4;
        @(posedge clk); #1;
        if(!v0 || d0!==32'haa000004) $fatal(1,"initial owner");
        @(negedge clk); q0=0; a0=32'h1000000c; q1=1; a1=32'h10000008;
        @(posedge clk); #1;
        if(!v0 || d0!==32'haa000004 || !v1 || d1!==32'hbb000008)
            $fatal(1,"independent responses or owner changed with address");
        @(negedge clk); q1=0;
        @(negedge clk); q1=1; a1=16; we1=1;
        repeat(3) begin
            @(posedge clk); #1;
            if(g1 || !v0 || d0!==32'haa000004 || writes!=0)
                $fatal(1,"backpressure failed");
        end
        @(negedge clk); r0=1;
        @(posedge clk); #1;
        if(v0 || !v1 || d1!==32'haa000010 || writes!=1)
            $fatal(1,"turnaround owner or write count");
        @(negedge clk); q1=0;
        repeat(2) @(negedge clk);
        if(v1 || writes!=1) $fatal(1,"duplicate store");
        $display("TEST_PASS RIB_OWNER cases=6");
        $finish;
    end
    initial begin #10000; $fatal(1,"owner test timeout"); end
endmodule
