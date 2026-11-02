// One ordered CPU transaction, toggle mailboxes across CPU/UI clocks.
// Native Pango HMIC interface: word addresses, 256-bit beats, no WVALID/RREADY/B.
// Each write is read back before completion; a coherent one-line read cache
// avoids four external reads for the four words of a TT entry.
module nc_ddr_bridge #(parameter CLEAR_BYTES=16777216)(
 input wire clk,rst_n,input wire req_valid,output wire req_ready,
 input wire req_write,req_clear,input wire[23:0] req_address,
 input wire[31:0] req_data,input wire[3:0] req_mask,
 output reg rsp_valid,input wire rsp_ready,output reg[63:0] rsp_line,
 output wire ready,output reg[31:0] reads,writes,cache_hits,wait_cycles,
 input wire ui_clk,ui_rst_n,init_done,
 output wire[27:0] axi_awaddr,output wire[3:0] axi_awlen,
 output wire axi_awvalid,input wire axi_awready,
 output wire[255:0] axi_wdata,output wire[31:0] axi_wstrb,input wire axi_wready,
 output wire[27:0] axi_araddr,output wire[3:0] axi_arlen,
 output wire axi_arvalid,input wire axi_arready,
 input wire[255:0] axi_rdata,input wire axi_rvalid,axi_rlast
);
 reg request_toggle,busy;
 reg[61:0] request_mailbox; // clear,write,address24,data32,mask4
 (* async_reg="true" *) reg ready_s1,ready_s2,done_s1,done_s2;
 reg ui_ready,done_toggle,response_hit;
 reg[63:0] response_mailbox;
 assign ready=ready_s2;
 assign req_ready=ready_s2 && !busy;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin ready_s1<=0;ready_s2<=0;done_s1<=0;done_s2<=0;end
  else begin ready_s1<=ui_ready;ready_s2<=ready_s1;done_s1<=done_toggle;done_s2<=done_s1;end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   request_toggle<=0;request_mailbox<=0;busy<=0;rsp_valid<=0;rsp_line<=0;
   reads<=0;writes<=0;cache_hits<=0;wait_cycles<=0;
  end else if(!ready_s2)begin request_toggle<=0;busy<=0;rsp_valid<=0;end
  else begin
   if(req_valid && req_ready)begin
    request_mailbox<={req_clear,req_write,req_address,req_data,req_mask};request_toggle<=!request_toggle;busy<=1;
    if(!req_clear)begin if(req_write)writes<=writes+1'b1;else reads<=reads+1'b1;end
   end
   if(busy && !rsp_valid)wait_cycles<=wait_cycles+1'b1;
   if(busy && !rsp_valid && done_s2==request_toggle)begin
    rsp_line<=response_mailbox;rsp_valid<=1;
    if(response_hit)cache_hits<=cache_hits+1'b1;
   end
   if(rsp_valid && rsp_ready)begin rsp_valid<=0;busy<=0;end
  end
 end
 (* async_reg="true" *) reg request_s1,request_s2;
 always @(posedge ui_clk or negedge ui_rst_n)begin
  if(!ui_rst_n)begin request_s1<=0;request_s2<=0;end
  else if(!init_done)begin request_s1<=0;request_s2<=0;end
  else begin request_s1<=request_toggle;request_s2<=request_s1;end
 end
 localparam WAIT_INIT=0,SCRUB_WRITE=1,SCRUB_ADDR=2,SCRUB_READ=3,IDLE=4,WRITE=5,READ_ADDR=6,READ_DATA=7,CHECK_RETURN=8;
 reg[3:0] state;
 reg aw_sent,verify_write,clear_request,scrub_bad;
 reg[4:0] beats;
 reg[27:0] scrub_address;
 reg[23:0] address;
 reg[31:0] data;
 reg[3:0] mask;
 reg cache_valid;
 reg[18:0] cache_tag;
 reg[255:0] cache_data;
 wire[31:0] word_mask={{8{mask[3]}},{8{mask[2]}},{8{mask[1]}},{8{mask[0]}}};
 wire[31:0] returned_word=cache_data >> {address[4:2],5'b0};
 wire aw_done=aw_sent || axi_awready;
 wire[5:0] accepted_beats={1'b0,beats}+(axi_wready?1'b1:1'b0);
 assign axi_awaddr=state==SCRUB_WRITE ? scrub_address : {6'b0,address[23:5],3'b0};
 assign axi_awlen=state==SCRUB_WRITE ? 4'd15 : 4'd0;
 assign axi_awvalid=(state==SCRUB_WRITE || state==WRITE) && !aw_sent;
 assign axi_wdata=state==SCRUB_WRITE ? 256'b0 : {8{data}};
 assign axi_wstrb=state==SCRUB_WRITE ? 32'hffffffff : ({28'b0,mask} << {address[4:2],2'b0});
 assign axi_araddr=state==SCRUB_ADDR ? scrub_address : {6'b0,address[23:5],3'b0};
 assign axi_arlen=state==SCRUB_ADDR ? 4'd15 : 4'd0;
 assign axi_arvalid=state==SCRUB_ADDR || state==READ_ADDR;
 always @(posedge ui_clk or negedge ui_rst_n)begin
  if(!ui_rst_n)begin
   state<=WAIT_INIT;ui_ready<=0;done_toggle<=0;response_mailbox<=0;response_hit<=0;
   aw_sent<=0;beats<=0;scrub_address<=0;scrub_bad<=0;clear_request<=0;
   address<=0;data<=0;mask<=0;cache_valid<=0;cache_tag<=0;cache_data<=0;verify_write<=0;
  end else if(!init_done)begin
   state<=WAIT_INIT;ui_ready<=0;done_toggle<=0;cache_valid<=0;aw_sent<=0;beats<=0;
  end else case(state)
   WAIT_INIT:begin scrub_address<=0;aw_sent<=0;beats<=0;clear_request<=0;state<=SCRUB_WRITE;end
   SCRUB_WRITE:begin
    if(axi_awvalid && axi_awready)aw_sent<=1;
    if(axi_wready && beats<16)beats<=beats+1'b1;
    if(aw_done && accepted_beats>=16)begin beats<=0;scrub_bad<=0;state<=SCRUB_ADDR;end
   end
   SCRUB_ADDR:if(axi_arready)begin beats<=0;scrub_bad<=0;state<=SCRUB_READ;end
   SCRUB_READ:if(axi_rvalid)begin
    if(axi_rdata!=0)scrub_bad<=1;
    beats<=beats+1'b1;
    if(axi_rlast)begin
     if(scrub_bad || axi_rdata!=0 || beats!=15)state<=SCRUB_ADDR;
     else if(scrub_address==(CLEAR_BYTES/4)-128)begin
      ui_ready<=1;state<=IDLE;
      if(clear_request)begin response_mailbox<=0;response_hit<=0;done_toggle<=request_s2;end
     end else begin scrub_address<=scrub_address+128;aw_sent<=0;beats<=0;state<=SCRUB_WRITE;end
    end
   end
   IDLE:if(request_s2!=done_toggle)begin
    response_hit<=0;
    address<=request_mailbox[59:36];data<=request_mailbox[35:4];mask<=request_mailbox[3:0];
    if(request_mailbox[61])begin
     clear_request<=1;cache_valid<=0;scrub_address<=0;aw_sent<=0;beats<=0;state<=SCRUB_WRITE;
    end else if(request_mailbox[60])begin aw_sent<=0;beats<=0;verify_write<=1;state<=WRITE;end
    else if(cache_valid && cache_tag==request_mailbox[59:41])begin
     response_mailbox<=cache_data >> {request_mailbox[40:39],6'b0};response_hit<=1;done_toggle<=request_s2;
    end else begin verify_write<=0;state<=READ_ADDR;end
   end
   WRITE:begin
    if(axi_awvalid && axi_awready)aw_sent<=1;
    if(axi_wready && beats<1)beats<=1;
    if(aw_done && accepted_beats>=1)begin cache_valid<=0;state<=READ_ADDR;end
   end
   READ_ADDR:if(axi_arready)state<=READ_DATA;
   // Reuse the existing cache-line FFs as the DDR ingress register.
   // No raw PHY data feeds the verification/64-bit publication mux this cycle.
   READ_DATA:if(axi_rvalid && axi_rlast)begin
    cache_data<=axi_rdata;cache_valid<=0;state<=CHECK_RETURN;
   end
   CHECK_RETURN:begin
    if(verify_write && ((returned_word^data)&word_mask)!=0)state<=READ_ADDR;
    else begin
     cache_tag<=address[23:5];cache_valid<=1;
     response_mailbox<=cache_data >> {address[4:3],6'b0};done_toggle<=request_s2;state<=IDLE;
    end
   end
   default:state<=WAIT_INIT;
  endcase
 end
endmodule
