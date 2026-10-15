`timescale 1ns/1ps
// Core-level variable-latency memory model. It deliberately separates request
// acceptance from response, exercising the frontend skid queue/redirect drain
// and EX operand preservation while MEM blocks the pipeline.
module cpu_latency_tb;
    parameter EARLY_LOCAL_REQUEST = 1;
    reg clk=0,rst_n=0;
    always #10 clk=~clk;
    wire[31:0] ia,da,dw;
    wire iq,ir,iv_ready,dq,dr,dwe,dv_ready;
    wire[3:0] ds;
    reg iv=0,dv=0;
    reg[31:0] idata=0,ddata=0,ipayload=0,dpayload=0;
    reg[31:0] imem[0:16383],dmem[0:8191];
    reg[31:0] timer_count=0,timer_value=0,timer_ctrl=0;
    reg timer_irq=0;
    integer icount=0,dcount=0,cycles=0,n,sentinel_writes=0;
    reg[2047:0] image;
    assign ir=icount==0 && !iv && cycles%3!=0;
    assign dr=dcount==0 && !dv && cycles%4!=0;
    tinyriscv_core #(.EARLY_LOCAL_REQUEST(EARLY_LOCAL_REQUEST)) dut(
        .clk(clk),.rst_n(rst_n),
        .ibus_addr_o(ia),.ibus_data_i(idata),.ibus_data_o(),.ibus_sel_o(),.ibus_we_o(),
        .ibus_req_valid_o(iq),.ibus_req_ready_i(ir),.ibus_rsp_valid_i(iv),.ibus_rsp_ready_o(iv_ready),
        .dbus_addr_o(da),.dbus_data_i(ddata),.dbus_data_o(dw),.dbus_sel_o(ds),.dbus_we_o(dwe),
        .dbus_req_valid_o(dq),.dbus_req_ready_i(dr),.dbus_rsp_valid_i(dv),.dbus_rsp_ready_o(dv_ready),
        .jtag_halt_i(1'b0),.int_i({7'b0,timer_irq})
    );
    initial begin
        if(!$value$plusargs("image=%s",image)) $fatal(1,"missing image");
        for(n=0;n<16384;n=n+1) imem[n]=0;
        for(n=0;n<8192;n=n+1) dmem[n]=0;
        $readmemh(image,imem);
        #80 rst_n=1;
        wait(dut.u_gpr_reg.regs[26]===32'd1);
        repeat(12) @(negedge clk);
        if(dut.u_gpr_reg.regs[27]!==32'd1)
            $fatal(1,"latency FAIL testnum=%0d",dut.u_gpr_reg.regs[3]);
        if(sentinel_writes!=1 || dmem[4]!==0)
            $fatal(1,"wrong-path/repeated store writes=%0d",sentinel_writes);
        $display("TEST_PASS LATENCY cycles=%0d",cycles);
        $finish;
    end
    always @(posedge clk) begin
        if(rst_n) begin
            cycles<=cycles+1;
            if(cycles>20000) $fatal(1,"latency timeout pc=%h",dut.ie_dec_pc_o);
            if(iv && iv_ready) iv<=0;
            if(dv && dv_ready) dv<=0;
            if(icount>0) begin
                icount<=icount-1;
                if(icount==1) begin iv<=1; idata<=ipayload; end
            end
            if(dcount>0) begin
                dcount<=dcount-1;
                if(dcount==1) begin dv<=1; ddata<=dpayload; end
            end
            if(iq && ir) begin
                icount<=1+cycles%4;
                ipayload<=imem[ia[15:2]];
            end
            if(timer_ctrl[0]) begin
                timer_count<=timer_count+1;
                if(timer_count>=timer_value) begin timer_irq<=1; timer_ctrl[0]<=0; end
            end else timer_count<=0;
            if(dq && dr) begin
                dcount<=1+cycles%5;
                case(da[31:28])
                    0: dpayload<=imem[da[15:2]];
                    1: dpayload<=dmem[da[14:2]];
                    2: dpayload<=da[3:0]==0 ? timer_ctrl : da[3:0]==4 ? timer_count : timer_value;
                    default: dpayload<=0;
                endcase
                if(dwe) begin
                    if(da[31:28]==1) begin
                        for(n=0;n<4;n=n+1)
                            if(ds[n]) dmem[da[14:2]][n*8+:8]<=dw[n*8+:8];
                        if(da==32'h10000010) sentinel_writes<=sentinel_writes+1;
                    end
                    if(da==32'h20000008) timer_value<=dw;
                    if(da==32'h20000000) begin
                        timer_ctrl<=dw;
                        if(dw[2]) timer_irq<=0;
                    end
                end
            end
        end
    end
endmodule
