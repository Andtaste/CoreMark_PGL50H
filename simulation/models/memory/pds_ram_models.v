`timescale 1ns/1ps
// Functional models for the current synchronous single-port RAMs.
// No vendor timing/netlist simulation is implied. Memory is retained on reset.
module ram1(input wire[31:0] wr_data, input wire[13:0] addr,
            input wire wr_en, clk, rst, input wire[3:0] wr_byte_en,
            output reg[31:0] rd_data);
    reg[31:0] memory[0:16383];
    integer b;
    always @(posedge clk or posedge rst) begin
        if (rst) rd_data <= 32'b0;
        else if (!wr_en) rd_data <= memory[addr];
    end
    always @(posedge clk) begin
        if (!rst && wr_en)
            for (b=0; b<4; b=b+1)
                if (wr_byte_en[b]) memory[addr][b*8+:8] <= wr_data[b*8+:8];
    end
endmodule

module ram2(input wire[31:0] wr_data, input wire[12:0] addr,
            input wire wr_en, clk, rst, input wire[3:0] wr_byte_en,
            output reg[31:0] rd_data);
    reg[31:0] memory[0:8191];
    reg[31:0] merged;
    integer b;
    always @(posedge clk or posedge rst) begin
        if (rst) rd_data <= 32'b0;
        else begin
            // Compute at the RAM clock edge, avoiding a combinational
            // sensitivity set covering all 8192 memory words.
            merged = memory[addr];
            for (b=0; b<4; b=b+1)
                if (wr_en && wr_byte_en[b]) merged[b*8+:8] = wr_data[b*8+:8];
            rd_data <= merged; // transparent write
            if (wr_en) memory[addr] <= merged;
        end
    end
endmodule
