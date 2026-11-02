#include "../xiangqi/engine.h"
extern "C" {
#include "../gomoku/engine.h"
Gomoku *g_platform_game(void);
extern unsigned char board_workspace[32400];
int board_run_coremark(unsigned iterations,int validation);
}
#include <string.h>
#ifdef HOST_BUILD
#include <stdio.h>
#include <time.h>
#ifdef _WIN32
#include <windows.h>
#endif
#else
#define MMIO(a) (*(volatile uint32_t *)(a))
#define UART(o) MMIO(0x20000000u+(o))
#endif
#ifndef CPU_HZ
#define CPU_HZ 80000000u
#endif
static unsigned game_id,time_ms=1000,max_depth=8;static uint32_t node_limit;
static int cancelled;static unsigned cancel_length;static char cancel_word[32];
static void output(char c){
#ifdef HOST_BUILD
 putchar(c);
#else
 while(!(UART(4)&1)){}UART(0)=(uint8_t)c;
#endif
}
static void text(const char *s){while(*s)output(*s++);}
static void number(uint64_t n){char b[20];unsigned k=0;do{b[k++]='0'+n%10;n/=10;}while(n);while(k)output(b[--k]);}
static void signed_number(int32_t n){if(n<0){output('-');number(0u-(uint32_t)n);}else number(n);}
static void newline(){text("\r\n");
#ifdef HOST_BUILD
 fflush(stdout);
#endif
}
static bool equal(const char *a,const char *b){while(*a&&*a==*b){a++;b++;}return *a==*b;}
static uint64_t cycles(){
#ifdef HOST_BUILD
#ifdef _WIN32
 LARGE_INTEGER v,f;QueryPerformanceCounter(&v);QueryPerformanceFrequency(&f);
 return (uint64_t)(v.QuadPart/f.QuadPart)*CPU_HZ+(uint64_t)(v.QuadPart%f.QuadPart)*CPU_HZ/f.QuadPart;
#else
 return (uint64_t)clock()*CPU_HZ/CLOCKS_PER_SEC;
#endif
#else
 uint32_t h,l,h2;do{__asm__ volatile("csrr %0,cycleh":"=r"(h));__asm__ volatile("csrr %0,cycle":"=r"(l));__asm__ volatile("csrr %0,cycleh":"=r"(h2));}while(h!=h2);return ((uint64_t)h<<32)|l;
#endif
}
static uint64_t instructions(){
#ifdef HOST_BUILD
 return 0;
#else
 uint32_t h,l,h2;do{__asm__ volatile("csrr %0,instreth":"=r"(h));__asm__ volatile("csrr %0,instret":"=r"(l));__asm__ volatile("csrr %0,instreth":"=r"(h2));}while(h!=h2);return ((uint64_t)h<<32)|l;
#endif
}
static int input(bool polling=false){
#ifdef HOST_BUILD
#ifdef _WIN32
 if(polling){DWORD bytes=0;if(!PeekNamedPipe(GetStdHandle(STD_INPUT_HANDLE),0,0,0,&bytes,0)||!bytes)return -1;}
#else
 if(polling)return -1;
#endif
 return getchar();
#else
 (void)polling;
 if(UART(8)&6){unsigned e=UART(8)&6;UART(8)=e;text("ERROR UART_RX");newline();}
 return (UART(8)&1)?(int)(UART(12)&255):-1;
#endif
}
extern "C" uint64_t board_cm_cycles(){return cycles();}
extern "C" uint64_t board_cm_instructions(){return instructions();}
extern "C" void board_cm_output(unsigned char c){if(c=='\n')output('\r');output((char)c);
#ifdef HOST_BUILD
 if(c=='\n')fflush(stdout);
#endif
}
static uint32_t ddr_counter(unsigned off){
#ifdef HOST_BUILD
 (void)off;return 0;
#else
 return MMIO(0x20004000u+off);
#endif
}
static bool ddr_ready(){
#ifdef HOST_BUILD
 return true;
#else
 return (ddr_counter(0)&1)!=0;
#endif
}
static void mode(unsigned id){
#ifndef HOST_BUILD
 MMIO(0x20006000u)=id==2;__asm__ volatile("fence rw,rw":::"memory");
#endif
 game_id=id;
}
static void hello(){text("HELLO ");text(game_id==1?"GOMOKU_V1":game_id==2?"XIANGQI_V1":"BOARD_GAMES_V1");text(" hz=");number(CPU_HZ);
#ifdef HOST_BUILD
 text(" platform=HOST_TEST");
#else
 text(" platform=FPGA");
#endif
 text(" games=GOMOKU,XIANGQI ddr_ready=");number(ddr_ready());newline();}
static void board(){
 if(!game_id){text("MENU GOMOKU XIANGQI");newline();return;}
 Gomoku *g=g_platform_game();text("BOARD ");number(game_id==1?g->side:xq_side());output(' ');number(game_id==1?g->winner:xq_outcome());output(' ');number(game_id==1?g->count:xq_ply());
 if(game_id==2){output(' ');number(xq_checked());}newline();
 unsigned w=game_id==1?15:9,h=game_id==1?15:10;const char *hex="0123456789ABCDE";
 for(unsigned y=0;y<h;y++){for(unsigned x=0;x<w;x++)output(hex[game_id==1?g_at(g,x,y):xq_get(y*9+x)]);newline();}text("END_BOARD");newline();
}
typedef struct {uint64_t start,budget;} Deadline;
static int stop_search(void *context){Deadline *d=(Deadline*)context;
 for(unsigned n=0;n<8;n++){int c=input(true);if(c<0)break;
  if(c==10||c==13){cancel_word[cancel_length]=0;if(equal(cancel_word,"STOP"))cancelled=1;else if(cancel_length){text("ERROR BUSY");newline();}cancel_length=0;}
  else if(cancel_length<sizeof(cancel_word)-1)cancel_word[cancel_length++]=(char)c;
 }
 return cancelled || cycles()-d->start>=d->budget;
}
static bool integer(const char **p,int *value){while(**p==' '||**p==',')(*p)++;if(**p<'0'||**p>'9')return false;unsigned n=0;while(**p>='0'&&**p<='9'){if(n>1000000)return false;n=n*10+(*(*p)++-'0');}*value=n;return true;}
static bool end(const char *p){while(*p==' ')p++;return !*p;}
static void move_line(unsigned side,int a,int b,const char *kind){text("MOVE ");number(side);output(' ');number(a);output(' ');number(b);output(' ');text(kind);newline();}
static void command(char *line){
 char *args=line;while(*args&&*args!=' ')args++;if(*args)*args++=0;const char *p=args;int a=0,b=0;Gomoku *g=g_platform_game();
 if(equal(line,"PING")&&end(p)){hello();return;}
 if(equal(line,"COREMARK")){
  a=6000;bool validation=false;
  if(!end(p)){
   if(!integer(&p,&a)||a<1||a>1000000){text("ERROR COREMARK_ARGS");newline();return;}
   while(*p==' ')p++;if(equal(p,"VALIDATION"))validation=true;
   else if(!end(p)){text("ERROR COREMARK_ARGS");newline();return;}
  }
  text("COREMARK BEGIN iterations=");number(a);newline();
  board_run_coremark((unsigned)a,validation);return;
 }
 if(equal(line,"SELECT")){
  unsigned id=equal(p,"GOMOKU")?1:equal(p,"XIANGQI")?2:0;
  if(!id){text("ERROR GAME");newline();return;}
  if(id==2&&!ddr_ready()){text("ERROR DDR_NOT_READY");newline();return;}
  mode(id);memset(board_workspace,0,32400);
  if(id==1){g_new(g);g_clear_table();}else{xq_init();xq_clear_tt();}
  max_depth=8;node_limit=0;hello();board();return;
 }
 if(equal(line,"MENU")&&end(p)){mode(0);hello();board();return;}
 if(equal(line,"STOP")&&end(p)){text("OK STOP");newline();return;}
 if(!game_id){text("ERROR SELECT_GAME");newline();return;}
 if(equal(line,"NEW")&&end(p)){if(game_id==1){g_new(g);g_clear_table();}else xq_new();text("OK NEW");newline();board();return;}
 if(equal(line,"SHOW")&&end(p)){board();return;}
 if(equal(line,"FEN")&&game_id==2){if(!xq_fen(p)){text("ERROR FEN");newline();return;}text("OK FEN");newline();board();return;}
 if(equal(line,"PLAY")&&integer(&p,&a)&&integer(&p,&b)&&end(p)){
  unsigned side=game_id==1?g->side:xq_side();int ok=game_id==1?g_play(g,a,b):!xq_outcome()&&xq_play(a,b);
  if(!ok){text("ERROR ILLEGAL_MOVE");newline();return;}move_line(side,a,b,"INPUT");board();return;
 }
 if(equal(line,"UNDO")&&integer(&p,&a)&&end(p)&&a>0&&a<=(game_id==1?g->count:xq_ply())){
  for(int i=0;i<a;i++){if(game_id==1)g_undo(g);else xq_undo();}if(game_id==1)g_clear_table();else xq_clear_tt();text("OK UNDO ");number(a);newline();board();return;
 }
 if(equal(line,"TIME")&&integer(&p,&a)&&end(p)&&a>=50&&a<=10000){time_ms=a;text("OK TIME ");number(a);newline();return;}
 if(equal(line,"DEPTH")&&integer(&p,&a)&&end(p)&&a>=1&&a<=(game_id==1?19:32)){max_depth=a;text("OK DEPTH ");number(a);newline();return;}
 if(equal(line,"LIMIT")&&integer(&p,&a)&&end(p)){node_limit=a;text("OK LIMIT ");number(a);newline();return;}
 if((equal(line,"GO")||equal(line,"HINT"))&&end(p)){
  bool hint=equal(line,"HINT");
  if(game_id==1?(g->winner||g->count==225):xq_outcome()){text("ERROR GAME_OVER");newline();return;}
  cancelled=0;cancel_length=0;Deadline d;d.budget=(uint64_t)time_ms*(CPU_HZ/1000);unsigned side=game_id==1?g->side:xq_side();
  uint32_t rd=ddr_counter(8),wr=ddr_counter(12),hit=ddr_counter(16),wait=ddr_counter(20);
  uint64_t ins=instructions();d.start=cycles();GResult gr={};XQResult xr={};
  if(game_id==1)gr=g_search(g,max_depth,node_limit,stop_search,&d);else xr=xq_search(max_depth,node_limit,stop_search,&d);
  uint64_t elapsed=cycles()-d.start,retired=instructions()-ins;
  text("INFO depth=");number(game_id==1?gr.depth:xr.depth);text(" nodes=");number(game_id==1?gr.nodes:xr.nodes);text(" score=");signed_number(game_id==1?gr.score:xr.score);
  text(" cycles=");number(elapsed);text(" instret=");number(retired);text(" tt_hits=");number(game_id==1?gr.tt_hits:xr.tt_hits);text(" cutoffs=");number(game_id==1?gr.cutoffs:xr.cutoffs);text(" stopped=");number(game_id==1?gr.stopped:xr.stopped);
  text(" qnodes=");number(game_id==1?0:xr.qnodes);text(" tt_probes=");number(game_id==1?0:xr.tt_probes);
  text(" ddr_reads=");number(ddr_counter(8)-rd);text(" ddr_writes=");number(ddr_counter(12)-wr);text(" ddr_hits=");number(ddr_counter(16)-hit);text(" ddr_wait=");number(ddr_counter(20)-wait);newline();
  if(cancelled){text("CANCELLED");newline();board();return;}
  a=game_id==1?gr.x:xq_move_from(xr.move);b=game_id==1?gr.y:xq_move_to(xr.move);
  if(hint){
   if(game_id==1?(a<0||b<0):!xr.move){text("ERROR SEARCH_MOVE");newline();return;}
   text("HINT ");number(side);text(" ");number(a);text(" ");number(b);newline();board();return;
  }
  if(game_id==1?(a<0||!g_play(g,a,b)):(!xr.move||!xq_play(a,b))){text("ERROR SEARCH_MOVE");newline();return;}move_line(side,a,b,"AI");board();return;
 }
 text("ERROR COMMAND");newline();
}
int main(){
#ifdef HOST_BUILD
 setvbuf(stdin,0,_IONBF,0);
#endif
 mode(0);hello();board();char line[256];unsigned length=0;bool overflow=false;
 for(;;){int c=input();
#ifdef HOST_BUILD
  if(c==EOF)return 0;
#endif
  if(c<0)continue;if(c==10||c==13){if(overflow){text("ERROR LINE_TOO_LONG");newline();}else if(length){line[length]=0;command(line);}length=0;overflow=false;}
  else if(c>=32&&c<127){if(length<sizeof(line)-1)line[length++]=c;else overflow=true;}
 }
}
