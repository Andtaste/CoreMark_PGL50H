/* Platform glue only; benchmark algorithms and CRC checks use sw/coremark. */
#include "../coremark/coremark.h"
extern uint64_t board_cm_cycles(void);
extern uint64_t board_cm_instructions(void);
extern void board_cm_output(unsigned char c);
volatile ee_s32 seed1_volatile,seed2_volatile,seed3_volatile=0x66;
volatile ee_s32 seed4_volatile=6000,seed5_volatile;
static uint64_t first,last,retired_first,retired_last;
int board_coremark_main(int argc,char **argv);
static void number64(uint64_t n){char b[21];unsigned k=0;do{b[k++]='0'+n%10;n/=10;}while(n);while(k)xputc(b[--k]);}
static void fixed(uint64_t n,uint64_t d){
 unsigned i;if(!d){xputs("unavailable");return;}number64(n/d);n%=d;xputc('.');
 for(i=0;i<6;i++){n*=10;xputc('0'+n/d);n%=d;}
}
void start_time(void){retired_first=board_cm_instructions();first=board_cm_cycles();}
void stop_time(void){last=board_cm_cycles();retired_last=board_cm_instructions();}
CORE_TICKS get_time(void){return last-first;}
secs_ret time_in_secs(CORE_TICKS ticks){return ticks/CPU_HZ;}
void portable_init(core_portable *p,int *argc,char **argv){
 (void)argc;(void)argv;*p=1;xdev_out(board_cm_output);
 xprintf("Configured CPU Hz : %lu\n",(unsigned long)CPU_HZ);
 xputs("Platform          : board-games SoC; software CoreMark, no game accelerator\n");
}
void portable_fini(core_portable *p){*p=0;}
void portable_print_timing(CORE_TICKS ticks,ee_u32 iterations){
 xputs("Total ticks      : ");number64(ticks);xputc('\n');
 xputs("Total time (secs): ");fixed(ticks,CPU_HZ);xputc('\n');
 xputs("Iterations/Sec   : ");fixed((uint64_t)iterations*CPU_HZ,ticks);xputc('\n');
 xputs("CoreMark/MHz     : ");fixed((uint64_t)iterations*1000000,ticks);xputc('\n');
 xputs("Retired instructions: ");number64(retired_last-retired_first);xputc('\n');
 xputs("IPC             : ");fixed(retired_last-retired_first,ticks);xputc('\n');
 xputs(ticks>=(uint64_t)CPU_HZ*10?"Duration >=10s; validity also requires CRC PASS\n":"DIAGNOSTIC ONLY: duration <10s; not a valid score\n");
}
int board_run_coremark(unsigned iterations,int validation){
 seed1_volatile=seed2_volatile=validation?0x3415:0;
 seed3_volatile=0x66;seed4_volatile=iterations;seed5_volatile=0;
 int result=board_coremark_main(0,0);
 xprintf("COREMARK END crc=%s valid=%s\n",result==1?"PASS":"FAIL",
#ifdef HOST_BUILD
 "NO_HOST_TEST"
#else
 result==1 && last-first>=(uint64_t)CPU_HZ*10?"YES":"NO_SHORT_RUN"
#endif
 );return result;
}
