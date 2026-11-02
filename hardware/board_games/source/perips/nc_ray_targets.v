// Candidate: return the first (rook) or second (cannon) occupied square
// in up/left/right/down order. Board occupancy follows accepted BRAM stores.
// A new board store invalidates an outstanding result; caller reissues query.
module nc_ray_targets #(parameter [31:0] BOARD_BASE=32'h10000004)(
 input wire clk,rst_n,write_valid,input wire[31:0] write_address,write_data,
 input wire[3:0] write_mask,input wire request,input wire[7:0] source,
 input wire second,input wire side,output wire ready,output reg[31:0] result);
 wire[255:0] occupied,black;
 wire board_write=write_valid && |write_mask && write_address>=BOARD_BASE && write_address<BOARD_BASE+256;
 genvar sq;
 generate for(sq=0;sq<256;sq=sq+1)begin:board
  if(sq/16>=3 && sq/16<=12 && sq%16>=3 && sq%16<=11)begin:valid
   localparam [31:0] ADDRESS=BOARD_BASE+sq;
   reg value,color;
   always @(posedge clk or negedge rst_n)
    if(!rst_n)begin value<=0;color<=0;end
    else if(write_valid && write_address[31:2]==ADDRESS[31:2] && write_mask[ADDRESS[1:0]])
     begin value<=|write_data[8*ADDRESS[1:0]+:8];color<=write_data[8*ADDRESS[1:0]+4];end
   assign occupied[sq]=value;assign black[sq]=color;
  end else begin assign occupied[sq]=0;assign black[sq]=0;end
 end endgenerate
 reg[8:0] row;reg[9:0] col;reg[7:0] origin;reg select_second,valid_source;
 reg[2:0] pending;reg result_valid;reg[31:0] raw_targets;reg[8:0] row_enemy;reg[9:0] col_enemy;
 wire source_valid=source[7:4]>=3 && source[7:4]<=12 && source[3:0]>=3 && source[3:0]<=11;
 integer i;
 function [3:0] target(input [9:0] mask,input [3:0] coordinate,input reverse,input want_second);
  integer k,j;reg[3:0] first,other;
  begin
   first=0;other=0;
   for(k=0;k<10;k=k+1)begin
    j=reverse?k:9-k;
    if(mask[j] && (reverse ? j+3<coordinate : j+3>coordinate))begin other=first;first=j+3;end
   end
   target=want_second?other:first;
  end
 endfunction
 wire[3:0] up=target(col,origin[7:4],1'b1,select_second);
 wire[3:0] left=target({1'b0,row},origin[3:0],1'b1,select_second);
 wire[3:0] right=target({1'b0,row},origin[3:0],1'b0,select_second);
 wire[3:0] down=target(col,origin[7:4],1'b0,select_second);
 assign ready=result_valid;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin row<=0;col<=0;row_enemy<=0;col_enemy<=0;raw_targets<=0;origin<=0;select_second<=0;valid_source<=0;pending<=0;result_valid<=0;result<=0;end
  else begin
   if(request)begin
    for(i=0;i<9;i=i+1)begin
     row[i]<=occupied[{source[7:4],4'b0}+i+3];
     row_enemy[i]<=black[{source[7:4],4'b0}+i+3]!=side;
    end
    for(i=0;i<10;i=i+1)begin
     col[i]<=occupied[(i+3)*16+source[3:0]];
     col_enemy[i]<=black[(i+3)*16+source[3:0]]!=side;
    end
    origin<=source;select_second<=second;valid_source<=source_valid;
    result_valid<=0;pending<=1;
   end else begin
    pending<={pending[1:0],1'b0};
    if(pending[0])begin
     raw_targets[7:0]<=valid_source && up!=0?{up,origin[3:0]}:8'b0;
     raw_targets[15:8]<=valid_source && left!=0?{origin[7:4],left}:8'b0;
     raw_targets[23:16]<=valid_source && right!=0?{origin[7:4],right}:8'b0;
     raw_targets[31:24]<=valid_source && down!=0?{down,origin[3:0]}:8'b0;
    end
    if(pending[1])begin
     result[7:0]<=raw_targets[7:0]!=0 && col_enemy[raw_targets[7:4]-3]?raw_targets[7:0]:8'b0;
     result[15:8]<=raw_targets[15:8]!=0 && row_enemy[raw_targets[11:8]-3]?raw_targets[15:8]:8'b0;
     result[23:16]<=raw_targets[23:16]!=0 && row_enemy[raw_targets[19:16]-3]?raw_targets[23:16]:8'b0;
     result[31:24]<=raw_targets[31:24]!=0 && col_enemy[raw_targets[31:28]-3]?raw_targets[31:24]:8'b0;
    end
    if(pending[2])result_valid<=1;
   end
   if(board_write)begin result_valid<=0;pending<=0;end
  end
 end
endmodule
