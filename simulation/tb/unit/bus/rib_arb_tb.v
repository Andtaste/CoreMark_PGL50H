`timescale 1ns/1ps
module rib_arb_tb;
    reg[31:0] ma[0:2], md[0:2];
    reg[3:0] ms[0:2];
    reg[2:0] req, we, rspready;
    reg[31:0] sd[0:4];
    reg[4:0] ready, valid;
    wire[31:0] mr_p[0:2], mr_l[0:2], mr_b[0:2];
    wire[2:0] ready_p, ready_l, ready_b, valid_p, valid_l, valid_b;
    wire[31:0] sa_p[0:4], sa_l[0:4], sa_b[0:4];
    wire[31:0] sw_p[0:4], sw_l[0:4], sw_b[0:4];
    wire[3:0] ss_p[0:4], ss_l[0:4], ss_b[0:4];
    wire[4:0] sr_p,sr_l,sr_b,se_p,se_l,se_b,rr_p,rr_l,rr_b;
    rib #(.MASTER_NUM(3),.SLAVE_NUM(5),.PARALLEL_ACCESS(1)) dut_p(
        .clk(1'b0),
        .rst_n(1'b1),
        .m0_addr_i(ma[0]),
        .m0_data_i(md[0]),
        .m0_sel_i(ms[0]),
        .m0_req_vld_i(req[0]),
        .m0_we_i(we[0]),
        .m0_rsp_rdy_i(rspready[0]),
        .m0_data_o(mr_p[0]),
        .m0_req_rdy_o(ready_p[0]),
        .m0_rsp_vld_o(valid_p[0]),
        .m1_addr_i(ma[1]),
        .m1_data_i(md[1]),
        .m1_sel_i(ms[1]),
        .m1_req_vld_i(req[1]),
        .m1_we_i(we[1]),
        .m1_rsp_rdy_i(rspready[1]),
        .m1_data_o(mr_p[1]),
        .m1_req_rdy_o(ready_p[1]),
        .m1_rsp_vld_o(valid_p[1]),
        .m2_addr_i(ma[2]),
        .m2_data_i(md[2]),
        .m2_sel_i(ms[2]),
        .m2_req_vld_i(req[2]),
        .m2_we_i(we[2]),
        .m2_rsp_rdy_i(rspready[2]),
        .m2_data_o(mr_p[2]),
        .m2_req_rdy_o(ready_p[2]),
        .m2_rsp_vld_o(valid_p[2]),
        .m3_addr_i(32'b0),
        .m3_data_i(32'b0),
        .m3_sel_i(4'b0),
        .m3_req_vld_i(1'b0),
        .m3_we_i(1'b0),
        .m3_rsp_rdy_i(1'b0),
        .s0_data_i(sd[0]),
        .s0_req_rdy_i(ready[0]),
        .s0_rsp_vld_i(valid[0]),
        .s0_addr_o(sa_p[0]),
        .s0_data_o(sw_p[0]),
        .s0_sel_o(ss_p[0]),
        .s0_req_vld_o(sr_p[0]),
        .s0_we_o(se_p[0]),
        .s0_rsp_rdy_o(rr_p[0]),
        .s1_data_i(sd[1]),
        .s1_req_rdy_i(ready[1]),
        .s1_rsp_vld_i(valid[1]),
        .s1_addr_o(sa_p[1]),
        .s1_data_o(sw_p[1]),
        .s1_sel_o(ss_p[1]),
        .s1_req_vld_o(sr_p[1]),
        .s1_we_o(se_p[1]),
        .s1_rsp_rdy_o(rr_p[1]),
        .s2_data_i(sd[2]),
        .s2_req_rdy_i(ready[2]),
        .s2_rsp_vld_i(valid[2]),
        .s2_addr_o(sa_p[2]),
        .s2_data_o(sw_p[2]),
        .s2_sel_o(ss_p[2]),
        .s2_req_vld_o(sr_p[2]),
        .s2_we_o(se_p[2]),
        .s2_rsp_rdy_o(rr_p[2]),
        .s3_data_i(sd[3]),
        .s3_req_rdy_i(ready[3]),
        .s3_rsp_vld_i(valid[3]),
        .s3_addr_o(sa_p[3]),
        .s3_data_o(sw_p[3]),
        .s3_sel_o(ss_p[3]),
        .s3_req_vld_o(sr_p[3]),
        .s3_we_o(se_p[3]),
        .s3_rsp_rdy_o(rr_p[3]),
        .s4_data_i(sd[4]),
        .s4_req_rdy_i(ready[4]),
        .s4_rsp_vld_i(valid[4]),
        .s4_addr_o(sa_p[4]),
        .s4_data_o(sw_p[4]),
        .s4_sel_o(ss_p[4]),
        .s4_req_vld_o(sr_p[4]),
        .s4_we_o(se_p[4]),
        .s4_rsp_rdy_o(rr_p[4])
    );
    rib #(.MASTER_NUM(3),.SLAVE_NUM(5),.PARALLEL_ACCESS(0)) dut_l(
        .clk(1'b0),
        .rst_n(1'b1),
        .m0_addr_i(ma[0]),
        .m0_data_i(md[0]),
        .m0_sel_i(ms[0]),
        .m0_req_vld_i(req[0]),
        .m0_we_i(we[0]),
        .m0_rsp_rdy_i(rspready[0]),
        .m0_data_o(mr_l[0]),
        .m0_req_rdy_o(ready_l[0]),
        .m0_rsp_vld_o(valid_l[0]),
        .m1_addr_i(ma[1]),
        .m1_data_i(md[1]),
        .m1_sel_i(ms[1]),
        .m1_req_vld_i(req[1]),
        .m1_we_i(we[1]),
        .m1_rsp_rdy_i(rspready[1]),
        .m1_data_o(mr_l[1]),
        .m1_req_rdy_o(ready_l[1]),
        .m1_rsp_vld_o(valid_l[1]),
        .m2_addr_i(ma[2]),
        .m2_data_i(md[2]),
        .m2_sel_i(ms[2]),
        .m2_req_vld_i(req[2]),
        .m2_we_i(we[2]),
        .m2_rsp_rdy_i(rspready[2]),
        .m2_data_o(mr_l[2]),
        .m2_req_rdy_o(ready_l[2]),
        .m2_rsp_vld_o(valid_l[2]),
        .m3_addr_i(32'b0),
        .m3_data_i(32'b0),
        .m3_sel_i(4'b0),
        .m3_req_vld_i(1'b0),
        .m3_we_i(1'b0),
        .m3_rsp_rdy_i(1'b0),
        .s0_data_i(sd[0]),
        .s0_req_rdy_i(ready[0]),
        .s0_rsp_vld_i(valid[0]),
        .s0_addr_o(sa_l[0]),
        .s0_data_o(sw_l[0]),
        .s0_sel_o(ss_l[0]),
        .s0_req_vld_o(sr_l[0]),
        .s0_we_o(se_l[0]),
        .s0_rsp_rdy_o(rr_l[0]),
        .s1_data_i(sd[1]),
        .s1_req_rdy_i(ready[1]),
        .s1_rsp_vld_i(valid[1]),
        .s1_addr_o(sa_l[1]),
        .s1_data_o(sw_l[1]),
        .s1_sel_o(ss_l[1]),
        .s1_req_vld_o(sr_l[1]),
        .s1_we_o(se_l[1]),
        .s1_rsp_rdy_o(rr_l[1]),
        .s2_data_i(sd[2]),
        .s2_req_rdy_i(ready[2]),
        .s2_rsp_vld_i(valid[2]),
        .s2_addr_o(sa_l[2]),
        .s2_data_o(sw_l[2]),
        .s2_sel_o(ss_l[2]),
        .s2_req_vld_o(sr_l[2]),
        .s2_we_o(se_l[2]),
        .s2_rsp_rdy_o(rr_l[2]),
        .s3_data_i(sd[3]),
        .s3_req_rdy_i(ready[3]),
        .s3_rsp_vld_i(valid[3]),
        .s3_addr_o(sa_l[3]),
        .s3_data_o(sw_l[3]),
        .s3_sel_o(ss_l[3]),
        .s3_req_vld_o(sr_l[3]),
        .s3_we_o(se_l[3]),
        .s3_rsp_rdy_o(rr_l[3]),
        .s4_data_i(sd[4]),
        .s4_req_rdy_i(ready[4]),
        .s4_rsp_vld_i(valid[4]),
        .s4_addr_o(sa_l[4]),
        .s4_data_o(sw_l[4]),
        .s4_sel_o(ss_l[4]),
        .s4_req_vld_o(sr_l[4]),
        .s4_we_o(se_l[4]),
        .s4_rsp_rdy_o(rr_l[4])
    );
    rib_baseline #(.MASTER_NUM(3),.SLAVE_NUM(5)) dut_b(
        .clk(1'b0),
        .rst_n(1'b1),
        .m0_addr_i(ma[0]),
        .m0_data_i(md[0]),
        .m0_sel_i(ms[0]),
        .m0_req_vld_i(req[0]),
        .m0_we_i(we[0]),
        .m0_rsp_rdy_i(rspready[0]),
        .m0_data_o(mr_b[0]),
        .m0_req_rdy_o(ready_b[0]),
        .m0_rsp_vld_o(valid_b[0]),
        .m1_addr_i(ma[1]),
        .m1_data_i(md[1]),
        .m1_sel_i(ms[1]),
        .m1_req_vld_i(req[1]),
        .m1_we_i(we[1]),
        .m1_rsp_rdy_i(rspready[1]),
        .m1_data_o(mr_b[1]),
        .m1_req_rdy_o(ready_b[1]),
        .m1_rsp_vld_o(valid_b[1]),
        .m2_addr_i(ma[2]),
        .m2_data_i(md[2]),
        .m2_sel_i(ms[2]),
        .m2_req_vld_i(req[2]),
        .m2_we_i(we[2]),
        .m2_rsp_rdy_i(rspready[2]),
        .m2_data_o(mr_b[2]),
        .m2_req_rdy_o(ready_b[2]),
        .m2_rsp_vld_o(valid_b[2]),
        .m3_addr_i(32'b0),
        .m3_data_i(32'b0),
        .m3_sel_i(4'b0),
        .m3_req_vld_i(1'b0),
        .m3_we_i(1'b0),
        .m3_rsp_rdy_i(1'b0),
        .s0_data_i(sd[0]),
        .s0_req_rdy_i(ready[0]),
        .s0_rsp_vld_i(valid[0]),
        .s0_addr_o(sa_b[0]),
        .s0_data_o(sw_b[0]),
        .s0_sel_o(ss_b[0]),
        .s0_req_vld_o(sr_b[0]),
        .s0_we_o(se_b[0]),
        .s0_rsp_rdy_o(rr_b[0]),
        .s1_data_i(sd[1]),
        .s1_req_rdy_i(ready[1]),
        .s1_rsp_vld_i(valid[1]),
        .s1_addr_o(sa_b[1]),
        .s1_data_o(sw_b[1]),
        .s1_sel_o(ss_b[1]),
        .s1_req_vld_o(sr_b[1]),
        .s1_we_o(se_b[1]),
        .s1_rsp_rdy_o(rr_b[1]),
        .s2_data_i(sd[2]),
        .s2_req_rdy_i(ready[2]),
        .s2_rsp_vld_i(valid[2]),
        .s2_addr_o(sa_b[2]),
        .s2_data_o(sw_b[2]),
        .s2_sel_o(ss_b[2]),
        .s2_req_vld_o(sr_b[2]),
        .s2_we_o(se_b[2]),
        .s2_rsp_rdy_o(rr_b[2]),
        .s3_data_i(sd[3]),
        .s3_req_rdy_i(ready[3]),
        .s3_rsp_vld_i(valid[3]),
        .s3_addr_o(sa_b[3]),
        .s3_data_o(sw_b[3]),
        .s3_sel_o(ss_b[3]),
        .s3_req_vld_o(sr_b[3]),
        .s3_we_o(se_b[3]),
        .s3_rsp_rdy_o(rr_b[3]),
        .s4_data_i(sd[4]),
        .s4_req_rdy_i(ready[4]),
        .s4_rsp_vld_i(valid[4]),
        .s4_addr_o(sa_b[4]),
        .s4_data_o(sw_b[4]),
        .s4_sel_o(ss_b[4]),
        .s4_req_vld_o(sr_b[4]),
        .s4_we_o(se_b[4]),
        .s4_rsp_rdy_o(rr_b[4])
    );

    integer i,j,k,n,winner,checks=0,seed=32'h51ab;
    reg[2:0] expected_ready,expected_valid;
    reg[31:0] expected_data[0:2];
    task check;
        begin
            #1;
            if ({ready_l,valid_l} !== {ready_b,valid_b})
                $fatal(1,"Legacy master control differs from baseline");
            for (i=0;i<3;i=i+1)
                if (mr_l[i] !== mr_b[i]) $fatal(1,"Legacy data differs");
            for (i=0;i<5;i=i+1)
                if ({sa_l[i],sw_l[i],ss_l[i],sr_l[i],se_l[i],rr_l[i]} !==
                    {sa_b[i],sw_b[i],ss_b[i],sr_b[i],se_b[i],rr_b[i]})
                    $fatal(1,"Legacy slave output differs at %0d",i);
            expected_ready=0; expected_valid=0;
            for (i=0;i<3;i=i+1) expected_data[i]=0;
            for (i=0;i<5;i=i+1) begin
                winner=-1;
                // Specification: highest priority requester for this address.
                for (j=2;j>=0;j=j-1)
                    if (winner==-1 && req[j] && ma[j][31:28]==i) winner=j;
                if (winner==-1) begin
                    if ({sa_p[i],sw_p[i],ss_p[i],sr_p[i],se_p[i],rr_p[i]} !== 71'b0)
                        $fatal(1,"Inactive slave has side effects");
                end else begin
                    if ({sa_p[i],sw_p[i],ss_p[i],sr_p[i],se_p[i],rr_p[i]} !==
                        {{4'b0,ma[winner][27:0]},md[winner],ms[winner],1'b1,we[winner],rspready[winner]})
                        $fatal(1,"Priority/address/write mask mismatch");
                    expected_ready[winner]=ready[i];
                    expected_valid[winner]=valid[i];
                    expected_data[winner]=sd[i];
                end
            end
            if ({ready_p,valid_p} !== {expected_ready,expected_valid})
                $fatal(1,"Parallel response control routing mismatch");
            for (i=0;i<3;i=i+1)
                if (mr_p[i] !== expected_data[i]) $fatal(1,"Parallel response data mismatch");
            checks=checks+1;
        end
    endtask
    initial begin
        req=0; we=0; rspready=7; ready=31; valid=31;
        for (k=0;k<3;k=k+1) begin ma[k]=k<<28; md[k]=32'hface0000+k; ms[k]=15; end
        for (k=0;k<5;k=k+1) sd[k]=32'hcafe0000+k;
        check;
        req=7; check;
        if (ready_p!==3'b111 || ready_l!==3'b100) $fatal(1,"Different slaves must operate concurrently");
        ma[0]=0; ma[1]=0; ma[2]=0; check;
        if (ready_p!==3'b100) $fatal(1,"Same slave must select JTAG");
        for (n=0;n<1000;n=n+1) begin
            req=$random(seed); we=$random(seed); rspready=$random(seed);
            ready=$random(seed); valid=$random(seed);
            for (k=0;k<3;k=k+1) begin ma[k]=$random(seed); md[k]=$random(seed); ms[k]=$random(seed); end
            for (k=0;k<5;k=k+1) sd[k]=$random(seed);
            check;
        end
        $display("TEST_PASS RIB cases=%0d",checks);
        $finish;
    end
endmodule
