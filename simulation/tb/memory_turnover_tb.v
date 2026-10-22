`timescale 1ns/1ps
module memory_turnover_tb;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,kill=0,valid=0,req_ready=0,rsp_valid=0,rsp_error=0;
 reg[279:0] packet=0;reg[31:0] rsp_data=0;
 wire ready,wb_valid,req_valid,req_write,rsp_ready,mul_consume;
 wire[279:0] wb_packet;wire[31:0] req_addr,req_data;wire[3:0] req_mask;
 nc_memory dut(.clk(clk),.rst_n(rst_n),.kill(kill),.valid(valid),.ready(ready),.packet(packet),
  .wb_valid(wb_valid),.wb_packet(wb_packet),.mul_tag(),.mul_ready(1'b0),.mul_data(32'b0),.mul_consume(mul_consume),
  .req_valid(req_valid),.req_ready(req_ready),.req_addr(req_addr),.req_data(req_data),.req_mask(req_mask),
  .req_write(req_write),.rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_data(rsp_data),.rsp_error(rsp_error));
 function[279:0] transaction;
  input[2:0] tag,f3;input[3:0] kind;input[31:0] address,data;
  begin transaction={tag,32'h100+{27'b0,tag,2'b0},32'h123,32'h104+{27'b0,tag,2'b0},
                      32'h0,address,data,32'b0,32'b0,5'b0,5'd10,f3,kind,(kind==4),1'b0,1'b0,1'b0};end
 endfunction
 task tick;begin @(posedge clk);#1;end endtask
 integer n,requests=0,responses=0,turnovers=0;
 reg[2:0] f3,tag;reg[31:0] raw,expected,store_value,load_address,shifted;
 reg[2:0] next_f3;reg[31:0] next_address;reg[279:0] captured_wb;
 reg held=0;reg[68:0] held_data;
 always @(posedge clk) if(rst_n) begin
  if(wb_valid) captured_wb<=wb_packet;
  if(held && (!req_valid || {req_write,req_mask,req_data,req_addr}!==held_data))
   $fatal(1,"published request changed under backpressure");
  held<=req_valid && !req_ready;held_data<={req_write,req_mask,req_data,req_addr};
  if(req_valid && req_ready) begin
   requests=requests+1;
   if(dut.state && rsp_valid) begin
    if(rsp_error) $fatal(1,"younger request accepted before older fault");
    turnovers=turnovers+1;
   end
  end
  if(rsp_valid && rsp_ready) responses=responses+1;
 end
 initial begin
  tick;@(negedge clk);rst_n=1;
  packet=transaction(3'b0,3'd2,5,32'h20003000,0);valid=0;req_ready=0;
  #1;if(!ready || req_valid || wb_valid || mul_consume) $fatal(1,"empty stale device payload counted as MEM wait");
  for(n=0;n<128;n=n+1) begin
   @(negedge clk);kill=1;valid=0;rsp_valid=0;tick;
   @(negedge clk);kill=0;valid=1;req_ready=1;rsp_error=0;tag=n%8;
   case(n%5) 0:f3=0;1:f3=1;2:f3=2;3:f3=4;default:f3=5;endcase
   load_address=32'h10000000+(f3[1] ? 0 : f3[0] ? (n&2) : (n&3));
   packet=transaction(tag,f3,4,load_address,0);
   #1;if(!req_valid || !ready) $fatal(1,"initial load not accepted");tick;
   @(negedge clk);
   raw=32'hfedcba98^n;store_value=32'habcdef00+n;
   packet=transaction(tag+3'd1,3'd2,5,32'h20003000,store_value);
   rsp_valid=1;rsp_data=raw;rsp_error=(n&4)!=0;req_ready=(n&1)!=0;
   shifted=raw >> (8*load_address[1:0]);
   case(f3) 0:expected={{24{shifted[7]}},shifted[7:0]};1:expected={{16{shifted[15]}},shifted[15:0]};
    4:expected={24'b0,shifted[7:0]};5:expected={16'b0,shifted[15:0]};default:expected=raw;endcase
   #1;
   if(!wb_valid || wb_packet[279:277]!==tag || wb_packet[180:149]!==expected)
    $fatal(1,"response lost old load context");
   if(rsp_error) begin
    if(req_valid || ready || !wb_packet[2] || wb_packet[20:16]!=5 || wb_packet[84:53]!==load_address)
     $fatal(1,"load fault did not suppress younger device write");
    tick;kill=1;
    #1;if(req_valid) $fatal(1,"WB fault failed to cancel younger store");
   end else begin
    if(!req_valid || ready!==req_ready || wb_packet[2]) $fatal(1,"successful turnover qualification");
    tick;
    @(negedge clk);rsp_valid=0;
    if(!req_ready) begin
     repeat(2) tick;
     @(negedge clk);req_ready=1;#1;
     if(!req_valid || req_addr!=32'h20003000 || req_data!==store_value) $fatal(1,"stalled successor lost");
     tick;@(negedge clk);
    end
    valid=0;rsp_valid=1;rsp_error=(n&2)!=0;rsp_data=0;
    #1;
    if(!wb_valid || wb_packet[279:277]!==((tag+3'd1)&3'd7)) $fatal(1,"store response context mismatch");
    if(rsp_error && (!wb_packet[2] || wb_packet[20:16]!=7 || wb_packet[84:53]!=32'h20003000))
     $fatal(1,"store fault cause or address mismatch");
    tick;@(negedge clk);rsp_valid=0;
   end
  end
  if(requests!=192 || responses!=192 || turnovers!=32) $fatal(1,"coverage requests=%0d responses=%0d turnovers=%0d",requests,responses,turnovers);
  // Consecutive loads change width, signedness and lane at every turnover.
  // The WB sink must sample the OLD shape while held captures the next one.
  @(negedge clk);kill=1;valid=0;rsp_valid=0;tick;
  @(negedge clk);kill=0;valid=1;req_ready=1;rsp_error=0;
  f3=0;load_address=32'h10000003;packet=transaction(0,f3,4,load_address,0);tick;
  for(n=0;n<16;n=n+1) begin
   @(negedge clk);rsp_valid=1;rsp_error=0;raw=32'h80017ffe^(n<<24);rsp_data=raw;
   case((n+1)%5) 0:next_f3=0;1:next_f3=1;2:next_f3=2;3:next_f3=4;default:next_f3=5;endcase
   next_address=32'h10000000+(next_f3[1] ? 0 : next_f3[0] ? (n&2) : (n&3));
   valid=n!=15;packet=transaction((n+1)%8,next_f3,4,next_address,0);
   shifted=raw>>(8*load_address[1:0]);
   case(f3) 0:expected={{24{shifted[7]}},shifted[7:0]};1:expected={{16{shifted[15]}},shifted[15:0]};
    4:expected={24'b0,shifted[7:0]};5:expected={16'b0,shifted[15:0]};default:expected=raw;endcase
   #1;if(!wb_valid || wb_packet[279:277]!==n%8 || wb_packet[180:149]!==expected) $fatal(1,"load-chain old response");
   tick;
   if(captured_wb[279:277]!==n%8 || captured_wb[180:149]!==expected) $fatal(1,"new load shape leaked into old WB");
   f3=next_f3;load_address=next_address;
  end
  if(requests!=208 || responses!=208 || turnovers!=47) $fatal(1,"load-chain coverage");
  $display("PASS memory turnover rounds=128 load_chain=16 requests=%0d responses=%0d turnovers=%0d stable-backpressure precise-faults",requests,responses,turnovers);$finish;
 end
endmodule
