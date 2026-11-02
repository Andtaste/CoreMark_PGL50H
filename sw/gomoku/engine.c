/* Original small-memory freestyle Gomoku engine. Search organization follows
 * conventional negamax/alpha-beta and iterative deepening. No Rapfi code copied.
 * Pattern scores and neighbour counts are updated only on affected lines.
 */
#include "engine.h"
#ifdef GOMOKU_HW
#define ACC ((volatile uint32_t *)0x20004000u)
static void acc_command(uint32_t cmd){ACC[1]=cmd;while(ACC[0]&1){} }
#endif
#define WIN 60000
#define MATE 10000000
#define INF 20000000
#define TT_SIZE 512
typedef struct {uint64_t key;int32_t score;uint16_t move;uint8_t depth,bound;} Entry;
static Entry table[TT_SIZE]; /* 8192 bytes on the target. */
static GMove lists[G_MAX_PLY][G_CANDIDATES];
static const int dirs[4]={1,17,18,16};
static uint32_t nodes,hits,cuts,limit;
static int interrupted;
static GStop stop_fn;static void *stop_context;
static uint32_t mix(uint32_t x){x^=x>>16;x*=0x7feb352du;x^=x>>15;x*=0x846ca68bu;return x^(x>>16);}
static uint64_t stone_key(unsigned p,unsigned s){uint32_t x=p*2+s;return ((uint64_t)mix(x+0x9e3779b9u)<<32)|mix(x+0x85ebca6bu);}
static uint64_t position_key(const Gomoku *g){return g->hash^(g->side==2?UINT64_C(0xd1b54a32d192ed03):0);}
static int valid(int p){int x=p%17,y=p/17;return x>0 && x<=15 && y>0 && y<=15;}
static unsigned pos(int x,int y){return (unsigned)((y+1)*17+x+1);}
int g_at(const Gomoku *g,int x,int y){return x<0||x>=15||y<0||y>=15?3:g->board[pos(x,y)];}
#include "pattern_table.h"
/* Both colors share the same board walk. Blocked means opponent OR wall;
 * the original evaluator treats those identically in every predicate. */
static uint32_t line_keys(const Gomoku *g,int p,int d){
 unsigned black=0,white=0;
 for(int sign=-1;sign<=1;sign+=2){
  int q=p,edge=0;
  for(unsigned n=0;n<4;n++){
   unsigned v=3;
   if(!edge){q+=sign*d;v=g->board[q];edge=v==3;}
   black*=3;white*=3;
   if(v){black+=v==1?1:2;white+=v==2?1:2;}
  }
 }
 return black|(white<<16);
}
static uint16_t line_score(const Gomoku *g,int p,int d,unsigned s){
 uint32_t key=line_keys(g,p,d);
 return g_line_patterns[s==1?(key&65535):(key>>16)];
}
static void refresh(Gomoku *g,int p,unsigned direction){
 unsigned black=0,white=0;
 if(!g->board[p]){
  uint32_t key=line_keys(g,p,dirs[direction]);
  black=g_line_patterns[key&65535];white=g_line_patterns[key>>16];
 }
 g->total[0]+=(int32_t)black-g->pattern[0][p][direction];g->pattern[0][p][direction]=(uint16_t)black;
 g->total[1]+=(int32_t)white-g->pattern[1][p][direction];g->pattern[1][p][direction]=(uint16_t)white;
}
static void changed(Gomoku *g,int p,int delta){
 for(int y=-2;y<=2;y++)for(int x=-2;x<=2;x++){
  int q=p+y*17+x;
  if(q>=0 && q<G_CELLS && valid(q))g->nearby[q]=(uint8_t)(g->nearby[q]+delta);
 }
#ifdef GOMOKU_HW
 acc_command((g->board[p]?2u:3u)|((unsigned)p<<8)|((unsigned)g->board[p]<<20));
#else
 for(unsigned d=0;d<4;d++){
  refresh(g,p,d);
  for(int sign=-1;sign<=1;sign+=2){
   int q=p;
   for(int n=1;n<=4;n++){q+=sign*dirs[d];if(g->board[q]==3)break;if(!g->board[q])refresh(g,q,d);}
  }
 }
#endif
}
static int won(const Gomoku *g,int p,unsigned s){
 for(unsigned d=0;d<4;d++){
  unsigned n=1;
  for(int sign=-1;sign<=1;sign+=2){int q=p+sign*dirs[d];while(g->board[q]==s){n++;q+=sign*dirs[d];}}
  if(n>=5)return 1;
 }
 return 0;
}
void g_clear_table(void){for(unsigned i=0;i<TT_SIZE;i++){table[i].key=0;table[i].bound=0;}}
void g_new(Gomoku *g){
 for(unsigned p=0;p<G_CELLS;p++){
  g->board[p]=valid((int)p)?0:3;g->nearby[p]=0;
#ifndef GOMOKU_HW
  for(unsigned s=0;s<2;s++)for(unsigned d=0;d<4;d++)g->pattern[s][p][d]=0;
#endif
 }
#ifdef GOMOKU_HW
 acc_command(1);
#endif
 g->side=1;g->winner=0;g->count=0;g->total[0]=g->total[1]=0;g->hash=0;
 // Isolated hypothetical stones score zero, so the zeroed cache is canonical.
}
int g_play(Gomoku *g,int x,int y){
 if(x<0||x>=15||y<0||y>=15||g->winner||g->count==225)return 0;
 unsigned p=pos(x,y),s=g->side;if(g->board[p])return 0;
 g->history[g->count++]=(uint16_t)p;g->board[p]=(uint8_t)s;g->hash^=stone_key(p,s);
 changed(g,(int)p,1);if(won(g,(int)p,s))g->winner=(uint8_t)s;
 g->side=(uint8_t)(3-s);return 1;
}
int g_undo(Gomoku *g){
 if(!g->count)return 0;
 unsigned p=g->history[--g->count],s=3-g->side;
 g->board[p]=0;g->hash^=stone_key(p,s);g->side=(uint8_t)s;g->winner=0;changed(g,(int)p,-1);return 1;
}
static int32_t point(const Gomoku *g,unsigned p,unsigned side){
#ifdef GOMOKU_HW
 (void)g;uint32_t pair=ACC[512+p];return side==1?(pair&65535):(pair>>16);
#else
 int32_t score=0;unsigned fours=0,threes=0;
 for(unsigned d=0;d<4;d++){unsigned v=g->pattern[side-1][p][d];if(v==WIN)return WIN;score+=(int32_t)v;fours+=v>=4000;threes+=v==800;}
 if(fours>=2)score+=30000;else if(fours && threes)score+=12000;else if(threes>=2)score+=6000;
 // Non-winning compound threats must never masquerade as an immediate win.
 return score>=WIN?WIN-1:score;
#endif
}
static void insert(GMove *m,unsigned *n,uint16_t p,int32_t rank){
 unsigned k=*n;
 if(k==G_CANDIDATES){if(rank<=m[k-1].rank)return;k--;}
 else (*n)++;
 while(k && rank>m[k-1].rank){m[k]=m[k-1];k--;}
 m[k].pos=p;m[k].rank=rank;
}
static unsigned generate(const Gomoku *g,GMove *m,uint16_t hint){
 if(!g->count){m[0].pos=pos(7,7);m[0].rank=0;return 1;}
 unsigned n=0;int wins=-1,blocks=0;
 for(int y=0;y<15;y++)for(int x=0;x<15;x++){
  unsigned p=pos(x,y);if(g->board[p] || !g->nearby[p])continue;
  int32_t own=point(g,p,g->side),enemy=point(g,p,3-g->side);
  if(own==WIN && wins<0)wins=(int)p;
  if(enemy==WIN)blocks++;
 }
 if(wins>=0){m[0].pos=(uint16_t)wins;m[0].rank=MATE;return 1;}
 for(int y=0;y<15;y++)for(int x=0;x<15;x++){
  unsigned p=pos(x,y);if(g->board[p] || !g->nearby[p])continue;
  int32_t own=point(g,p,g->side),enemy=point(g,p,3-g->side);
  if(blocks && enemy!=WIN)continue;
  int32_t rank=own*2+enemy+(x<=7?x:14-x)+(y<=7?y:14-y);
  insert(m,&n,(uint16_t)p,rank);
 }
 for(unsigned i=1;i<n;i++)if(m[i].pos==hint){GMove t=m[i];for(unsigned j=i;j;j--)m[j]=m[j-1];m[0]=t;break;}
 return n;
}
static int stop_now(void){
 if((limit && nodes>=limit) || (stop_fn && stop_fn(stop_context))){interrupted=1;return 1;}return 0;
}
static int32_t evaluate(const Gomoku *g){
#ifdef GOMOKU_HW
 int32_t black=(int32_t)ACC[2],white=(int32_t)ACC[3];
 int32_t v=g->side==1?black-white:white-black;
#else
 int32_t v=g->total[g->side-1]-g->total[2-g->side];
#endif
 if(v>500000)v=500000;
 if(v< -500000)v= -500000;
 return v;
}
static int32_t negamax(Gomoku *g,unsigned depth,unsigned ply,int32_t alpha,int32_t beta,uint16_t *best){
 if(stop_now())return 0;
 nodes++;
 if(g->winner)return -MATE+(int32_t)ply;
 if(g->count==225)return 0;
 if(!depth || ply==G_MAX_PLY-1)return evaluate(g);
 uint64_t key=position_key(g);Entry *e=&table[(uint32_t)key&(TT_SIZE-1)];uint16_t hint=0;
 if(e->bound && e->key==key){
  hint=e->move;
  if(ply && e->depth>=depth){
   int32_t s=e->score;if(s>MATE-1000)s-=(int32_t)ply;else if(s< -MATE+1000)s+=(int32_t)ply;
   if(e->bound==1 || (e->bound==2 && s>=beta) || (e->bound==3 && s<=alpha)){hits++;return s;}
  }
 }
 unsigned n=generate(g,lists[ply],hint);if(!n)return 0;
 int32_t original=alpha,value=-INF;uint16_t chosen=lists[ply][0].pos;
 for(unsigned i=0;i<n;i++){
  unsigned p=lists[ply][i].pos;uint16_t ignored=0;
  g_play(g,(int)(p%17)-1,(int)(p/17)-1);
  int32_t score=-negamax(g,depth-1,ply+1,-beta,-alpha,&ignored);
  g_undo(g);if(interrupted)return 0;
  if(score>value){value=score;chosen=(uint16_t)p;}
  if(score>alpha)alpha=score;
  if(alpha>=beta){cuts++;break;}
 }
 *best=chosen;e->key=key;e->move=chosen;e->depth=(uint8_t)depth;
 e->bound=(uint8_t)(value<=original?3:value>=beta?2:1);
 e->score=value;if(value>MATE-1000)e->score+=(int32_t)ply;else if(value< -MATE+1000)e->score-=(int32_t)ply;
 return value;
}
GResult g_search(Gomoku *g,unsigned depth,uint32_t node_limit,GStop stop,void *context){
 GResult r={0,0,0,0,-1,-1,0,0};nodes=hits=cuts=0;interrupted=0;limit=node_limit;stop_fn=stop;stop_context=context;
 if(g->winner || g->count==225)return r;
 unsigned n=generate(g,lists[0],0);if(!n)return r;
 uint16_t chosen=lists[0][0].pos;r.x=(int16_t)(chosen%17-1);r.y=(int16_t)(chosen/17-1);
 if(depth>=G_MAX_PLY)depth=G_MAX_PLY-1;
 for(unsigned d=1;d<=depth;d++){
  uint16_t best=chosen;
  int32_t score=negamax(g,d,0,-INF,INF,&best);
  if(interrupted)break;
  chosen=best;r.x=(int16_t)(best%17-1);r.y=(int16_t)(best/17-1);r.score=score;r.depth=(uint8_t)d;
  if(score>MATE-1000 || score< -MATE+1000)break;
 }
 r.nodes=nodes;r.tt_hits=hits;r.cutoffs=cuts;r.stopped=(uint8_t)interrupted;return r;
}
int g_consistent(const Gomoku *g){
 int32_t totals[2]={0,0};uint64_t hash=0;
 for(int p=0;p<G_CELLS;p++)if(valid(p)){
  if(g->board[p])hash^=stone_key((unsigned)p,g->board[p]);
  unsigned near=0;
  for(int y=-2;y<=2;y++)for(int x=-2;x<=2;x++){int q=p+y*17+x;if(q>=0&&q<G_CELLS&&valid(q)&&g->board[q]>0&&g->board[q]<3)near++;}
  if(near!=g->nearby[p])return 0;
  for(unsigned s=0;s<2;s++)for(unsigned d=0;d<4;d++){
   uint16_t v=g->board[p]?0:line_score(g,p,dirs[d],s+1);
#ifdef GOMOKU_HW
   uint32_t pair=ACC[2048+(unsigned)p*4+d];
   if(v!=(s?(pair>>16):(pair&65535)))return 0;
#else
   if(v!=g->pattern[s][p][d])return 0;
#endif
   totals[s]+=v;
  }
 }
#ifdef GOMOKU_HW
 return hash==g->hash && totals[0]==(int32_t)ACC[2] && totals[1]==(int32_t)ACC[3];
#else
 return hash==g->hash && totals[0]==g->total[0] && totals[1]==g->total[1];
#endif
}
