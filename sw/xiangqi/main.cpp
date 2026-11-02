#include "engine.h"
#ifdef HOST_BUILD
#include <stdio.h>
#include <time.h>
#ifdef _WIN32
#include <windows.h>
#endif
#else
#define UART(off) (*(volatile uint32_t *)(0x20000000u+(off)))
#endif
#ifndef CPU_HZ
#define CPU_HZ 80000000u
#endif

static unsigned time_ms=1000,max_depth=8;static uint32_t node_limit;
static int cancelled;static unsigned cancel_length;
static char cancel_word[16];
static void output(char c){
#ifdef HOST_BUILD
 putchar(c);
#else
 while(!(UART(4)&1)){}UART(0)=(uint8_t)c;
#endif
}
static void text(const char *s){while(*s)output(*s++);}
static void number(uint64_t n){char b[20];unsigned k=0;do{b[k++]='0'+(unsigned)(n%10);n/=10;}while(n);while(k)output(b[--k]);}
static void signed_number(int32_t n){if(n<0){output('-');number((uint32_t)(-n));}else number((uint32_t)n);}
static void newline(void){text("\r\n");
#ifdef HOST_BUILD
 fflush(stdout);
#endif
}
static uint64_t cycles(void){
#ifdef HOST_BUILD
#ifdef _WIN32
 LARGE_INTEGER v,f;QueryPerformanceCounter(&v);QueryPerformanceFrequency(&f);
 return (uint64_t)((v.QuadPart%f.QuadPart)*CPU_HZ/f.QuadPart)+(uint64_t)(v.QuadPart/f.QuadPart)*CPU_HZ;
#else
 return (uint64_t)clock()*CPU_HZ/CLOCKS_PER_SEC;
#endif
#else
 uint32_t h,l,h2;do{__asm__ volatile("csrr %0, cycleh":"=r"(h));__asm__ volatile("csrr %0, cycle":"=r"(l));__asm__ volatile("csrr %0, cycleh":"=r"(h2));}while(h!=h2);return ((uint64_t)h<<32)|l;
#endif
}
static uint64_t instructions(void){
#ifdef HOST_BUILD
 return 0;
#else
 uint32_t h,l,h2;do{__asm__ volatile("csrr %0, instreth":"=r"(h));__asm__ volatile("csrr %0, instret":"=r"(l));__asm__ volatile("csrr %0, instreth":"=r"(h2));}while(h!=h2);return ((uint64_t)h<<32)|l;
#endif
}
static int equal(const char *a,const char *b){while(*a && *a==*b){a++;b++;}return *a==*b;}
static int input(void){
#ifdef HOST_BUILD
 return getchar();
#else
 if(UART(8)&6){unsigned e=UART(8)&6;UART(8)=e;text("ERROR UART_RX");newline();}
 return (UART(8)&1)?(int)(UART(12)&255):-1;
#endif
}
static int search_input(void){
#ifdef HOST_BUILD
#ifdef _WIN32
 DWORD bytes=0;
 if(!PeekNamedPipe(GetStdHandle(STD_INPUT_HANDLE),0,0,0,&bytes,0) || !bytes)return -1;
 return getchar();
#else
 return -1;
#endif
#else
 return (UART(8)&1)?(int)(UART(12)&255):-1;
#endif
}
typedef struct {uint64_t start,budget;} Deadline;
static int stop_search(void *context){
 Deadline *d=(Deadline *)context;
// The desktop sends only STOP while thinking; all other controls are disabled.
 for(unsigned n=0;n<8;n++){
  int c=search_input();if(c<0)break;
  if(c==10 || c==13){cancel_word[cancel_length]=0;if(equal(cancel_word,"STOP"))cancelled=1;cancel_length=0;}
  else if(cancel_length<15)cancel_word[cancel_length++]=(char)c;
 }
 return cancelled || cycles()-d->start>=d->budget;
}
static int integer(const char **p,int *value){
 while(**p==' ' || **p==',')(*p)++;
 if(**p<'0'||**p>'9')return 0;
 unsigned n=0;
 while(**p>='0'&&**p<='9'){unsigned d=(unsigned)(*(*p)++-'0');if(n>1000000)return 0;n=n*10+d;}
 *value=(int)n;return 1;
}
static int end(const char *p){while(*p==' ')p++;return !*p;}
static void board(void){
 text("BOARD ");number(xq_side());output(' ');number(xq_outcome());output(' ');number(xq_ply());output(' ');number(xq_checked());newline();
 const char *hex="0123456789ABCDE";
 for(int y=0;y<10;y++){for(int x=0;x<9;x++)output(hex[xq_get(y*9+x)]);newline();}
 text("END_BOARD");newline();
}
static void hello(void){text("HELLO XIANGQI_V1 hz=");number(CPU_HZ);
#ifdef HOST_BUILD
 text(" platform=HOST_TEST");
#else
 text(" platform=FPGA");
#endif
 text(" size=9x10 tt_bytes=16777216 history_bytes=32400");
#if defined(XQ_ATTACK_ACCEL) && !defined(HOST_BUILD)
 text(" attack_accel=1");
#endif
 newline();}
static void move_line(unsigned side,int from,int to,const char *kind){
 text("MOVE ");number(side);output(' ');number(from);output(' ');number(to);output(' ');text(kind);newline();
}
static uint32_t ddr_counter(unsigned offset){
#ifdef HOST_BUILD
 (void)offset;return 0;
#else
 return UART(0x4000+offset);
#endif
}
static void command(char *line){
 char *args=line;while(*args && *args!=' ')args++;if(*args)*args++=0;
 const char *p=args;int a=0,b=0;
 if(equal(line,"PING") && end(p)){hello();return;}
 if(equal(line,"NEW") && end(p)){xq_new();text("OK NEW");newline();board();return;}
 if(equal(line,"SHOW") && end(p)){board();return;}
 if(equal(line,"FEN")){
  if(!xq_fen(p)){text("ERROR FEN");newline();return;}
  text("OK FEN");newline();board();return;
 }
 if(equal(line,"PLAY") && integer(&p,&a) && integer(&p,&b) && end(p)){
  unsigned side=(unsigned)xq_side();
  if(xq_outcome() || !xq_play(a,b)){text("ERROR ILLEGAL_MOVE");newline();return;}
  move_line(side,a,b,"INPUT");board();return;
 }
 if(equal(line,"UNDO") && integer(&p,&a) && end(p) && a>0 && a<=xq_ply()){
  for(int i=0;i<a;i++)xq_undo();xq_clear_tt();text("OK UNDO ");number((unsigned)a);newline();board();return;
 }
 if(equal(line,"TIME") && integer(&p,&a) && end(p) && a>=50 && a<=10000){time_ms=(unsigned)a;text("OK TIME ");number(time_ms);newline();return;}
 if(equal(line,"DEPTH") && integer(&p,&a) && end(p) && a>=1 && a<=32){max_depth=(unsigned)a;text("OK DEPTH ");number(max_depth);newline();return;}
 if(equal(line,"LIMIT") && integer(&p,&a) && end(p) && a>=0){node_limit=(uint32_t)a;text("OK LIMIT ");number(node_limit);newline();return;}
 if(equal(line,"STOP") && end(p)){text("OK STOP");newline();return;}
 if(equal(line,"GO") && end(p)){
  if(xq_outcome()){text("ERROR GAME_OVER");newline();return;}
  cancelled=0;cancel_length=0;Deadline d;d.budget=(uint64_t)time_ms*(CPU_HZ/1000);
  uint32_t rd=ddr_counter(8),wr=ddr_counter(12),hit=ddr_counter(16),wait=ddr_counter(20);
  uint64_t ins=instructions();d.start=cycles();
  XQResult r=xq_search(max_depth,node_limit,stop_search,&d);
  uint64_t elapsed=cycles()-d.start,retired=instructions()-ins;
  uint32_t rd_delta=ddr_counter(8)-rd,wr_delta=ddr_counter(12)-wr,hit_delta=ddr_counter(16)-hit,wait_delta=ddr_counter(20)-wait;
  text("INFO depth=");number((unsigned)r.depth);text(" nodes=");number(r.nodes);text(" score=");signed_number(r.score);
  text(" cycles=");number(elapsed);text(" instret=");number(retired);text(" tt_hits=");number(r.tt_hits);
  text(" cutoffs=");number(r.cutoffs);text(" stopped=");number((unsigned)r.stopped);text(" qnodes=");number(r.qnodes);
  text(" tt_probes=");number(r.tt_probes);text(" ddr_reads=");number(rd_delta);text(" ddr_writes=");number(wr_delta);
  text(" ddr_hits=");number(hit_delta);text(" ddr_wait=");number(wait_delta);newline();
  if(cancelled){text("CANCELLED");newline();board();return;}
  unsigned side=(unsigned)xq_side();int from=xq_move_from(r.move),to=xq_move_to(r.move);
  if(!r.move || !xq_play(from,to)){text("ERROR SEARCH_MOVE");newline();return;}
  move_line(side,from,to,"AI");board();return;
 }
 text("ERROR COMMAND");newline();
}
int main(void){
#ifdef HOST_BUILD
 setvbuf(stdin,0,_IONBF,0);
#endif
 xq_init();hello();char line[256];unsigned length=0;int overflow=0;
 for(;;){int c=input();
#ifdef HOST_BUILD
  if(c==EOF)return 0;
#endif
  if(c<0)continue;
  if(c==10 || c==13){
   if(overflow){text("ERROR LINE_TOO_LONG");newline();}else if(length){line[length]=0;command(line);}
   length=0;overflow=0;
  }else if(c>=32 && c<127){if(length<sizeof(line)-1)line[length++]=(char)c;else overflow=1;}
 }
}
