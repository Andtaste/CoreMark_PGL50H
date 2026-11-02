// Xiangqi check detector. Observe accepted writes to the real BRAM board;
// software never copies a board through MMIO. Results cover both players.
// Three registered logic boundaries keep board-to-MMIO logic off CPU paths.
module nc_attack_check #(parameter [31:0] BOARD_BASE=32'h10000004)(
 input wire clk,rst_n,write_valid,input wire[31:0] write_address,write_data,
 input wire[3:0] write_mask,output wire ready,output reg[1:0] checks);
 wire[4:0] board_piece[0:255];
 wire board_write=write_valid && |write_mask &&
  write_address>=BOARD_BASE && write_address<BOARD_BASE+256;
 reg[2:0] settled;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)settled<=0;else if(board_write)settled<=0;else settled<={settled[1:0],1'b1};
 assign ready=&settled;
 genvar square;
 generate for(square=0;square<256;square=square+1)begin:board
  if(square/16>=3 && square/16<=12 && square%16>=3 && square%16<=11)begin:valid_square
   localparam [31:0] ADDRESS=BOARD_BASE+square;
   reg[4:0] value;
   always @(posedge clk or negedge rst_n)
    if(!rst_n)value<=0;
    else if(write_valid && write_address[31:2]==ADDRESS[31:2] && write_mask[ADDRESS[1:0]])
     value<=write_data[8*ADDRESS[1:0]+:5];
   assign board_piece[square]=value;
  end else begin:outside
   assign board_piece[square]=0;
  end
 end endgenerate
 function integer delta(input integer direction);
  case(direction)0:delta=-16;1:delta=-1;2:delta=1;default:delta=16;endcase
 endfunction
 function integer leg(input integer index);
  case(index/2)0:leg=-17;1:leg=-15;2:leg=15;default:leg=17;endcase
 endfunction
 function integer horse(input integer index);
  case(index)0:horse=-33;1:horse=-18;2:horse=-31;3:horse=-14;
   4:horse=14;5:horse=31;6:horse=18;default:horse=33;endcase
 endfunction
 reg[8:0] king_checks[0:1];
 genvar side,king,direction,step,h;
 generate for(side=0;side<2;side=side+1)begin:player
  for(king=0;king<9;king=king+1)begin:palace
   localparam ROW=(side==0 ? 10 : 3)+king/3,COL=6+king%3;
   localparam KS=ROW*16+COL,OWN=side==0 ? 8 : 16,OPP=side==0 ? 16 : 8;
   wire[10:0] short_hits;
   assign short_hits[0]=board_piece[KS+(side==0 ? -16 : 16)]==OPP+6;
   assign short_hits[1]=board_piece[KS-1]==OPP+6;
   assign short_hits[2]=board_piece[KS+1]==OPP+6;
   for(h=0;h<8;h=h+1)begin:knight
    assign short_hits[3+h]=board_piece[KS+leg(h)]==0 && board_piece[KS+horse(h)]==OPP+3;
   end
   reg[4:0] groups;reg king_present;
   always @(posedge clk)begin groups[0]<=|short_hits;king_present<=board_piece[KS]==OWN;end
   for(direction=0;direction<4;direction=direction+1)begin:ray
    localparam LENGTH=direction==0 ? ROW-3 : direction==1 ? COL-3 : direction==2 ? 11-COL : 12-ROW;
    wire[8:0] occupied,hits;
    for(step=0;step<9;step=step+1)begin:target
     if(step<LENGTH)begin:on_ray
      localparam TS=KS+(step+1)*delta(direction);
      localparam [8:0] PRIOR=(9'd1<<step)-1;
      wire[8:0] blockers=occupied & PRIOR;
      wire empty_path=blockers==0;
      wire one_screen=blockers!=0 && (blockers & (blockers-9'd1))==0;
      assign occupied[step]=board_piece[TS]!=0;
      assign hits[step]=(empty_path && (board_piece[TS]==OPP+4 || board_piece[TS]==OPP)) ||
                       (one_screen && board_piece[TS]==OPP+5);
     end else begin:outside
      assign occupied[step]=0;assign hits[step]=0;
     end
    end
    always @(posedge clk)groups[direction+1]<=|hits;
   end
   always @(posedge clk)king_checks[side][king]<=king_present && |groups;
  end
 end endgenerate
 always @(posedge clk or negedge rst_n)
  if(!rst_n)checks<=0;else checks<={|king_checks[1],|king_checks[0]};
endmodule
