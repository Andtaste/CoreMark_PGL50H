/* Bare-metal/desktop interface for the adapted GPL-2.0 XQWLight engine. */
extern "C" void xq_clear_tt(void){
#ifdef HOST_BUILD
 memset(host_tt,0,sizeof(host_tt));
#else
 /* The DDR bridge acknowledges only after its full 16MiB scrub completes. */
 *(volatile uint32_t *)0x20004004u=1;
 __asm__ volatile("fence rw,rw":::"memory");
#endif
}
extern "C" void xq_init(void){InitZobrist();pos.Startup();memset(history,0,sizeof(history));}
extern "C" void xq_new(void){pos.Startup();xq_clear_tt();memset(history,0,sizeof(history));}
extern "C" int xq_get(int square){
 if(square<0 || square>=90)return -1;
 unsigned pc=pos.ucpcSquares[Mailbox90((unsigned)square)];
 return pc==0?0:pc<16?(int)pc-7:(int)pc-8;
}
extern "C" int xq_side(void){return pos.sdPlayer;}
extern "C" int xq_ply(void){return pos.nMoveNum-1;}
extern "C" int xq_checked(void){return pos.Checked();}
extern "C" int xq_legal(int from,int to){
 if(from<0||from>=90||to<0||to>=90||from==to)return 0;
 int mv=MOVE(Mailbox90((unsigned)from),Mailbox90((unsigned)to));
 if(!pos.LegalMove(mv) || !pos.MakeMove(mv))return 0;
 pos.UndoMakeMove();return 1;
}
extern "C" int xq_play(int from,int to){
 if(pos.nMoveNum>=MAX_MOVES-LIMIT_DEPTH-2 || !xq_legal(from,to))return 0;
 pos.nDistance=0;
 if(!pos.MakeMove(MOVE(Mailbox90((unsigned)from),Mailbox90((unsigned)to))))return 0;
 pos.nDistance=0;return 1;
}
extern "C" int xq_undo(void){
 if(pos.nMoveNum<=1)return 0;
 pos.UndoMakeMove();pos.nDistance=0;return 1;
}
extern "C" int xq_outcome(void){
 int repeated=pos.RepStatus(3);
 if(repeated){int value=pos.RepValue(repeated);return value>WIN_VALUE?pos.sdPlayer+1:value< -WIN_VALUE?2-pos.sdPlayer:3;}
 return pos.IsMate()?2-pos.sdPlayer:0;
}
extern "C" int xq_fen(const char *fen){
 PositionStruct parsed;parsed.ClearBoard();int x=0,y=0,kings[2]={0,0},counts[2][7]={{0}};
 while(*fen && *fen!=' '){
  char c=*fen++;
  if(c=='/'){if(x!=9||y>=9)return 0;x=0;y++;continue;}
  if(c>='1'&&c<='9'){x+=c-'0';if(x>9)return 0;continue;}
  if(x>=9||y>=10)return 0;
  int side=c>='a'&&c<='z';char lower=side?c:(char)(c+'a'-'A');
  if(lower=='h')lower='n';
  if(lower=='e')lower='b';
  const char *types="kabnrcp",*t=strchr(types,lower);if(!t)return 0;
  int type=(int)(t-types);if(++counts[side][type]>(type==0?1:type==6?5:2))return 0;
  if(type==0){if(x<3||x>5||(side?y>2:y<7))return 0;kings[side]++;}
  parsed.AddPiece(Mailbox90((unsigned)(y*9+x)),(side?16:8)+type);x++;
 }
 if(x!=9||y!=9||kings[0]!=1||kings[1]!=1||*fen!=' ')return 0;
 while(*fen==' ')fen++;
 if(*fen!='w'&&*fen!='r'&&*fen!='b')return 0;
 if(*fen=='b')parsed.ChangeSide();
 fen++;
 /* This small protocol accepts only board + side, not FEN move counters. */
 while(*fen==' ')fen++;
 if(*fen)return 0;
 parsed.ChangeSide();int previousInCheck=parsed.Checked();parsed.ChangeSide();
 if(previousInCheck)return 0;
 parsed.SetIrrev();pos=parsed;xq_clear_tt();memset(history,0,sizeof(history));return 1;
}
extern "C" uint64_t xq_perft(unsigned depth){
 if(!depth)return 1;
 int moves[MAX_GEN_MOVES],n=pos.GenerateMoves(moves);uint64_t total=0;
 for(int i=0;i<n;i++)if(pos.MakeMove(moves[i])){total+=xq_perft(depth-1);pos.UndoMakeMove();}
 return total;
}
extern "C" int xq_move_from(int move){return (int)Square90(SRC(move));}
extern "C" int xq_move_to(int move){return (int)Square90(DST(move));}
extern "C" uint32_t xq_history_bytes(void){return sizeof(history);}
extern "C" uint32_t xq_tt_bytes(void){return (uint32_t)HASH_SIZE*sizeof(HashItem);}
extern "C" XQResult xq_search(unsigned depth,uint32_t limit,XQStop stop,void *context){
 memset(&info,0,sizeof(info));node_limit=limit;stop_fn=stop;stop_context=context;pos.nDistance=0;
 memset(history,0,sizeof(history));memset(Search.mvKillers,0,sizeof(Search.mvKillers));
 int moves[MAX_GEN_MOVES],n=pos.GenerateMoves(moves),best=0;
 for(int i=0;i<n;i++)if(pos.MakeMove(moves[i])){pos.UndoMakeMove();best=moves[i];break;}
 if(!best || xq_outcome()){info.move=0;return info;}
 int score=pos.Evaluate();if(depth>=LIMIT_DEPTH)depth=LIMIT_DEPTH-1;
 for(unsigned d=1;d<=depth;d++){
  Search.mvResult=best;int value=SearchRoot((int)d);
  if(info.stopped)break;
  best=Search.mvResult;score=value;info.depth=(int)d;
  if(value>WIN_VALUE||value< -WIN_VALUE)break;
 }
 info.move=best;info.score=score;return info;
}
