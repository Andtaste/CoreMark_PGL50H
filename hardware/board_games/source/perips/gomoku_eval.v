// Stateful, same-clock MMIO evaluator. CPU retains search/TT/order and sends
// one command per play/undo. All memories have synchronous registered reads.
// Scoring is bit-exact with sw/gomoku's original pattern and compound rules.
module gomoku_eval #(parameter PATTERN_FILE="memory/pattern.hex")(
 input clk,rst_n,command,input[31:0] command_data,
 input read,input[13:0] read_offset,output reg[31:0] rdata,
 output busy
);
 localparam IDLE=0,CLEAR=1,WRITE_BOARD=2,TARGET=3,TARGET_WAIT=4,TARGET_CHECK=5,
 LINE_NEXT=6,LINE_WAIT=7,LINE_ADD=8,LOOKUP=9,UPDATE=10,
 AGG_START=11,AGG_WAIT=12,AGG_ADD=13,FORM=14,CLAMP=15,POINT_WRITE=16,ADVANCE=17;
 reg[4:0]state;assign busy=state!=IDLE;
 reg[10:0]clear_index;reg[4:0]clear_x,clear_y;
 reg[8:0]move_pos,target,walk,board_addr;reg[1:0]stone,axis;
 reg[3:0]offset_index;reg[2:0]digit;reg edge_seen;
 reg[12:0]black_key,white_key;reg[10:0]pattern_addr;
 reg[1:0]agg_axis;reg[17:0]sum_b,sum_w,formed_b,formed_w;
 reg[2:0]fours_b,fours_w,threes_b,threes_w;reg win_b,win_w;
 reg[31:0]point_value;reg signed[31:0]total_b,total_w;
 reg[1:0]board_q;reg[31:0]pattern_q;reg[15:0]rom_b,rom_w;
 reg[1:0]board_mem[0:511];
 reg[31:0]patterns[0:2047];
 reg[31:0]points[0:511];
 reg[15:0]rom[0:8191];
 initial $readmemh(PATTERN_FILE,rom);
 wire[5:0]direction=axis==0?6'd1:axis==1?6'd17:axis==2?6'd18:6'd16;
 wire[8:0]next_walk=digit<4?walk-direction:walk+direction;
 wire[1:0]sample=edge_seen?2'd3:board_q;
 wire[12:0]next_black=black_key*13'd3+(sample==0?13'd0:sample==1?13'd1:13'd2);
 wire[12:0]next_white=white_key*13'd3+(sample==0?13'd0:sample==2?13'd1:13'd2);
 wire[15:0]vb=pattern_q[15:0],vw=pattern_q[31:16];
 wire target_is_center=offset_index==0;
 wire pattern_write=state==CLEAR || state==UPDATE;
 wire[10:0]pattern_wa=state==CLEAR?clear_index:{target,axis};
 wire[31:0]pattern_wd=state==CLEAR?32'd0:target_is_center && stone!=0?32'd0:{rom_w,rom_b};
 wire[8:0]point_wa=state==CLEAR?clear_index[8:0]:target;
 wire point_write=(state==CLEAR && clear_index<512)||state==POINT_WRITE;
 wire board_write=(state==CLEAR && clear_index<512)||state==WRITE_BOARD;
 wire[8:0]board_wa=state==CLEAR?clear_index[8:0]:move_pos;
 wire[1:0]board_wd=state==CLEAR?(clear_y>0 && clear_y<=15 && clear_x>0 && clear_x<=15?2'd0:2'd3):stone;
 // Port A read/write uses a single address, old-data read semantics. Port B
 // is a read-only diagnostic port; it is not used during normal searches.
 always @(posedge clk)begin
  if(board_write)board_mem[board_wa]<=board_wd;
  board_q<=board_mem[board_addr];
  if(pattern_write)patterns[pattern_wa]<=pattern_wd;
  pattern_q<=patterns[pattern_addr];
  if(point_write)points[point_wa]<=state==CLEAR?32'd0:point_value;
  rom_b<=rom[black_key];rom_w<=rom[white_key];
  if(read)begin
   if(read_offset[13])rdata<=patterns[read_offset[12:2]];
   else if(read_offset[11])rdata<=points[read_offset[10:2]];
   else case(read_offset[10:0])
    0:rdata<={31'd0,busy};8:rdata<=total_b;12:rdata<=total_w;
    default:rdata<=0;
   endcase
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   state<=IDLE;clear_index<=0;clear_x<=0;clear_y<=0;
   move_pos<=0;target<=0;walk<=0;board_addr<=0;stone<=0;axis<=0;offset_index<=0;
   digit<=0;edge_seen<=0;black_key<=0;white_key<=0;pattern_addr<=0;
   agg_axis<=0;sum_b<=0;sum_w<=0;formed_b<=0;formed_w<=0;
   fours_b<=0;fours_w<=0;threes_b<=0;threes_w<=0;win_b<=0;win_w<=0;
   point_value<=0;total_b<=0;total_w<=0;
  end else case(state)
   IDLE:if(command)begin
    if(command_data[1:0]==1)begin
     clear_index<=0;clear_x<=0;clear_y<=0;total_b<=0;total_w<=0;state<=CLEAR;
    end else if(command_data[1])begin
     move_pos<=command_data[16:8];stone<=command_data[1:0]==3?2'd0:command_data[21:20];
     state<=WRITE_BOARD;
    end
   end
   CLEAR:begin
    if(clear_index==2047)state<=IDLE;else clear_index<=clear_index+1'b1;
    if(clear_x==16)begin clear_x<=0;clear_y<=clear_y+1'b1;end else clear_x<=clear_x+1'b1;
   end
   WRITE_BOARD:begin axis<=0;offset_index<=0;target<=move_pos;state<=TARGET;end
   TARGET:begin board_addr<=target;pattern_addr<={target,axis};state<=TARGET_WAIT;end
   TARGET_WAIT:state<=TARGET_CHECK;
   TARGET_CHECK:begin
    if(board_q==3)begin
     // Sentinel terminates this half-line; no speculative read beyond border.
     if(offset_index<5)offset_index<=4;else offset_index<=8;
     state<=ADVANCE;
    end else if(board_q!=0 && !target_is_center)state<=ADVANCE;
    else if(board_q!=0)state<=UPDATE;
    else begin walk<=target;digit<=0;edge_seen<=0;black_key<=0;white_key<=0;state<=LINE_NEXT;end
   end
   LINE_NEXT:begin
    if(!edge_seen)begin walk<=next_walk;board_addr<=next_walk;end
    state<=LINE_WAIT;
   end
   LINE_WAIT:state<=LINE_ADD;
   LINE_ADD:begin
    black_key<=next_black;white_key<=next_white;
    if(sample==3)edge_seen<=1;
    if(digit==7)state<=LOOKUP;
    else begin
     digit<=digit+1'b1;
     if(digit==3)begin walk<=target;edge_seen<=0;end
     state<=LINE_NEXT;
    end
   end
   LOOKUP:state<=UPDATE;
   UPDATE:begin
    total_b<=total_b+$signed({16'd0,pattern_wd[15:0]})-$signed({16'd0,pattern_q[15:0]});
    total_w<=total_w+$signed({16'd0,pattern_wd[31:16]})-$signed({16'd0,pattern_q[31:16]});
    agg_axis<=0;sum_b<=0;sum_w<=0;fours_b<=0;fours_w<=0;threes_b<=0;threes_w<=0;
    win_b<=0;win_w<=0;state<=AGG_START;
   end
   AGG_START:begin pattern_addr<={target,agg_axis};state<=AGG_WAIT;end
   AGG_WAIT:state<=AGG_ADD;
   AGG_ADD:begin
    sum_b<=sum_b+vb;sum_w<=sum_w+vw;
    fours_b<=fours_b+(vb>=4000);fours_w<=fours_w+(vw>=4000);
    threes_b<=threes_b+(vb==800);threes_w<=threes_w+(vw==800);
    win_b<=win_b || vb==60000;win_w<=win_w || vw==60000;
    if(agg_axis==3)state<=FORM;
    else begin agg_axis<=agg_axis+1'b1;state<=AGG_START;end
   end
   FORM:begin
    formed_b<=sum_b+(fours_b>=2?18'd30000:fours_b!=0 && threes_b!=0?18'd12000:threes_b>=2?18'd6000:18'd0);
    formed_w<=sum_w+(fours_w>=2?18'd30000:fours_w!=0 && threes_w!=0?18'd12000:threes_w>=2?18'd6000:18'd0);
    state<=CLAMP;
   end
   CLAMP:begin
    point_value<={win_w?16'd60000:formed_w>=60000?16'd59999:formed_w[15:0],win_b?16'd60000:formed_b>=60000?16'd59999:formed_b[15:0]};
    state<=POINT_WRITE;
   end
   POINT_WRITE:state<=ADVANCE;
   ADVANCE:begin
    if(offset_index==8)begin
     if(axis==3)state<=IDLE;
     else begin axis<=axis+1'b1;offset_index<=0;target<=move_pos;state<=TARGET;end
    end else begin
     offset_index<=offset_index+1'b1;
     if(offset_index==0)target<=move_pos-direction;
     else if(offset_index==4)target<=move_pos+direction;
     else if(offset_index<4)target<=target-direction;
     else target<=target+direction;
     state<=TARGET;
    end
   end
   default:state<=IDLE;
  endcase
 end
endmodule
