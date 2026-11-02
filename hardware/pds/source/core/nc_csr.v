// M-only CSR bank, direct/vectored trap entry, three distinct IRQ sources.
module nc_csr(input wire clk,rst_n,retire,retire1,
 input wire[13:0] stats_events,
 input wire[11:0] raddr,output reg[31:0] rdata,output reg exists,writable,
 input wire we,input wire[11:0] waddr,input wire[31:0] wdata,
 input wire trap,mret,input wire[31:0] trap_pc,trap_cause,trap_value,
 input wire irq_soft,irq_timer,irq_ext,
 output wire irq_pending,output wire[31:0] irq_cause,
 output wire[31:0] trap_base,return_pc,output wire vector_mode);
 reg[31:0] mstatus,mie,mtvec,mscratch,mepc,mcause,mtval;
 reg[63:0] cycles,instret;
 wire[31:0] stats_data;
 nc_stats stats(.clk(clk),.rst_n(rst_n),.events(stats_events),
  .control(we && waddr==12'h7c0),.control_data(wdata),.addr(raddr[3:0]),.data(stats_data));
 wire[31:0] mip={20'b0,irq_ext,3'b0,irq_timer,3'b0,irq_soft,3'b0};
 wire[31:0] enabled=mip & mie;
 assign irq_pending=mstatus[3] && |enabled;
 assign irq_cause=enabled[11] ? 32'h8000000b : enabled[3] ? 32'h80000003 : 32'h80000007;
 assign trap_base={mtvec[31:2],2'b0};assign vector_mode=mtvec[1:0]==1;
 assign return_pc={mepc[31:2],2'b0};
 always @* begin
  exists=1;writable=1;rdata=0;
  case(raddr)
   12'h300:rdata=mstatus;
   12'h301:begin rdata=32'h40001100;writable=0;end // RV32 I+M, M-only
   12'h304:rdata=mie;
   12'h305:rdata=mtvec;
   12'h340:rdata=mscratch;
   12'h341:rdata=mepc;
   12'h342:rdata=mcause;
   12'h343:rdata=mtval;
   12'h344:begin rdata=mip;writable=0;end
   12'hb00:rdata=cycles[31:0];12'hb80:rdata=cycles[63:32];
   12'hb02:rdata=instret[31:0];12'hb82:rdata=instret[63:32];
   12'hc00:begin rdata=cycles[31:0];writable=0;end
   12'hc80:begin rdata=cycles[63:32];writable=0;end
   12'hc02:begin rdata=instret[31:0];writable=0;end
   12'hc82:begin rdata=instret[63:32];writable=0;end
   12'hf11,12'hf12,12'hf13,12'hf14:begin rdata=0;writable=0;end
   default:begin
    if(raddr[11:4]==8'h7c) begin rdata=stats_data;writable=raddr[3:0]==0;end
    else begin exists=0;writable=0;end
   end
  endcase
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   mstatus<=32'h1800;mie<=0;mtvec<=0;mscratch<=0;mepc<=0;mcause<=0;mtval<=0;cycles<=0;instret<=0;
  end else begin
   cycles<=cycles+1'b1;
   if(retire) instret<=instret+(retire1 ? 64'd2 : 64'd1);
   if(we) case(waddr)
    12'h300:mstatus<=32'h1800 | (wdata & 32'h88);
    12'h304:mie<=wdata & 32'h888;
    12'h305:mtvec<={wdata[31:2],1'b0,wdata[1:0]==1};
    12'h340:mscratch<=wdata;
    12'h341:mepc<={wdata[31:2],2'b0};
    12'h342:mcause<=wdata;12'h343:mtval<=wdata;
    12'hb00:cycles[31:0]<=wdata;12'hb80:cycles[63:32]<=wdata;
    12'hb02:instret[31:0]<=wdata;12'hb82:instret[63:32]<=wdata;
    default:;
   endcase
   if(mret) mstatus<=32'h1880 | (mstatus[7] ? 32'h8 : 0);
   if(trap) begin
    mepc<={trap_pc[31:2],2'b0};mcause<=trap_cause;mtval<=trap_value;
    mstatus<=32'h1800 | (mstatus[3] ? 32'h80 : 0);
   end
  end
 end
endmodule
