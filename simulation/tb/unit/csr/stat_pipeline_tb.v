`timescale 1ns/1ps
// Check event retiming against the original window/clear/saturation semantics.
module stat_pipeline_tb;
    reg clk=0,rst_n=0,we=0;
    always #5 clk=~clk;
    reg[7:0] events=0;
    reg[31:0] wdata=0;
    wire[31:0] rdata;
    csr_reg dut(.clk(clk),.rst_n(rst_n),.stat_events_i(events),
        .exu_we_i(we),.exu_waddr_i(32'h7c0),.exu_wdata_i(wdata),
        .exu_raddr_i(32'h7c2),.exu_rdata_o(rdata),.clint_we_i(1'b0),
        .clint_waddr_i(32'b0),.clint_wdata_i(32'b0),
        .mtvec_o(),.mepc_o(),.mie_o(),.mstatus_o());
    reg enabled=0;
    reg[31:0] ref_count[0:7];
    reg[7:0] ref_overflow=0;
    reg[32:0] visible;
    reg overflow;
    integer j,k,checks=0;
    always @(posedge clk) begin
        if(!rst_n) begin
            enabled=0; ref_overflow=0;
            for(j=0;j<8;j=j+1) ref_count[j]=0;
        end else begin
            if(we) begin
                enabled=wdata[0];
                if(wdata[1]) begin
                    ref_overflow=0;
                    for(j=0;j<8;j=j+1) ref_count[j]=0;
                end
            end else if(enabled) begin
                for(j=0;j<8;j=j+1) if(events[j]) begin
                    if(&ref_count[j]) ref_overflow[j]=1;
                    else ref_count[j]=ref_count[j]+1;
                end
            end
            #1;
            for(j=0;j<8;j=j+1) begin
                visible={1'b0,dut.stat_count[j]}+dut.stat_pending[j];
                if(visible[32]) visible={1'b0,32'hffffffff};
                overflow=dut.stat_overflow[j] ||
                    (dut.stat_pending[j] && &dut.stat_count[j]);
                if(visible[31:0]!==ref_count[j] || overflow!==ref_overflow[j])
                    $fatal(1,"event retiming mismatch counter=%0d",j);
                if(!enabled && (dut.stat_count[j]!==ref_count[j] ||
                    dut.stat_overflow[j]!==ref_overflow[j] || dut.stat_pending[j]))
                    $fatal(1,"stop did not drain final event");
            end
            checks=checks+1;
        end
    end
    initial begin
        repeat(3) @(negedge clk);
        rst_n=1;
        // Preload only to exercise the 32-bit saturation boundary quickly.
        dut.stat_count[1]=32'hfffffffe; ref_count[1]=32'hfffffffe;
        for(k=0;k<240;k=k+1) begin
            events=k<8 ? 8'hff : (k*37)^8'h53;
            we=k==0 || k==5 || k==6 || k%23==0 || k%23==1 || k%23==2;
            wdata=k==0 ? 1 : k==5 ? 0 : k==6 ? 3 :
                k%23==0 ? 0 : k%23==1 ? 1 : 3;
            @(negedge clk);
        end
        we=1; wdata=0;
        @(negedge clk);
        we=0; events=8'hff;
        repeat(3) @(negedge clk);
        $display("TEST_PASS STAT_PIPELINE checks=%0d",checks);
        $finish;
    end
endmodule
