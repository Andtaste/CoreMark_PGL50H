#include <stdio.h>
#include <stdlib.h>
#include "coremark.h"
#include "../include/utils.h"
#include "../include/uart.h"
#include "../include/xprintf.h"

#if VALIDATION_RUN
	volatile ee_s32 seed1_volatile=0x3415;
	volatile ee_s32 seed2_volatile=0x3415;
	volatile ee_s32 seed3_volatile=0x66;
#endif

#if PERFORMANCE_RUN
	volatile ee_s32 seed1_volatile=0x0;
	volatile ee_s32 seed2_volatile=0x0;
	volatile ee_s32 seed3_volatile=0x66;
#endif

#if PROFILE_RUN
	volatile ee_s32 seed1_volatile=0x8;
	volatile ee_s32 seed2_volatile=0x8;
	volatile ee_s32 seed3_volatile=0x8;
#endif

volatile ee_s32 seed4_volatile=ITERATIONS;
volatile ee_s32 seed5_volatile=0;

static CORE_TICKS t0, t1;
static int stats_present;
static int stats_version;
static uint32_t stats[8];
static uint32_t retired_instructions;

/* Memory clobbers keep benchmark memory accesses within the measurement
 * boundaries. These custom CSRs are implemented by csr_reg.v. */
#define STAT_READ(addr) ({ uint32_t value; \
    __asm__ volatile ("csrr %0, " #addr : "=r"(value) :: "memory"); value; })
#define STAT_CONTROL(value) \
    __asm__ volatile ("csrw 0x7c0, %0" :: "r"((uint32_t)(value)) : "memory")

static void print_u64(const char *label, uint64_t value)
{
    char text[21];
    char *cursor = text + sizeof(text) - 1;
    *cursor = '\0';
    do {
        *--cursor = '0' + value % 10;
        value /= 10;
    } while (value);
    xprintf("%s%s\n", label, cursor);
}

static void print_stat(const char *label, uint32_t value, int cycles)
{
    xprintf("%s%lu", label, (unsigned long)value);
    if (cycles && stats[0] && !(stats[7] & 0x7f)) {
        uint32_t percent = (uint32_t)((uint64_t)value * 10000 / stats[0]);
        xprintf(" (%lu.%02lu%%)", (unsigned long)(percent / 100),
                (unsigned long)(percent % 100));
    }
    xprintf("\n");
}

/* Fixed-point ratios avoid floating-point printf support on RV32. */
static void print_ratio(const char *label, uint32_t numerator, uint32_t denominator)
{
    uint64_t scaled = (uint64_t)numerator * 1000 / denominator;
    xprintf("%s%lu.%03lu\n", label, (unsigned long)(scaled / 1000),
            (unsigned long)(scaled % 1000));
}

void start_time(void)
{
  if (stats_present) STAT_CONTROL(3); /* clear and enable */
  __asm__ volatile ("" ::: "memory");
  t0 = get_cycle_value();
  __asm__ volatile ("" ::: "memory");
}

void stop_time(void)
{
  __asm__ volatile ("" ::: "memory");
  t1 = get_cycle_value();
  __asm__ volatile ("" ::: "memory");
  if (stats_present) {
      STAT_CONTROL(0); /* freeze before reading/printing */
      stats[0] = STAT_READ(0x7c1);
      stats[1] = STAT_READ(0x7c2);
      stats[2] = STAT_READ(0x7c3);
      stats[3] = STAT_READ(0x7c4);
      stats[4] = STAT_READ(0x7c5);
      stats[5] = STAT_READ(0x7c6);
      stats[6] = STAT_READ(0x7c7);
      stats[7] = STAT_READ(0x7c8);
      if (stats_version >= 2) retired_instructions = STAT_READ(0x7c9);
  }
}

CORE_TICKS get_time(void)
{
  return t1 - t0;
}

secs_ret time_in_secs(CORE_TICKS ticks)
{
  // scale timer down to avoid uint64_t -> double conversion in RV32
  int scale = 256;
  uint32_t delta = ticks / scale;
  uint32_t freq = CPU_FREQ_HZ / scale;
  return delta / (double)freq;
}

void portable_init(core_portable *p, int *argc, char *argv[])
{
    uint32_t signature;
    uart_init();
    signature = STAT_READ(0x7cf);
    stats_version = signature == 0x53544102 ? 2 :
                    signature == 0x53544101 ? 1 : 0;
    stats_present = stats_version != 0;
}

void portable_fini(core_portable *p)
{
    (void)p;
    xprintf("\nCPU statistics v%d\n", stats_present ? stats_version : 2);
    print_u64("Benchmark cycles64 : ", t1 - t0);
    if (!stats_present) {
        xprintf("Stats CSR unavailable: rebuild/download the new FPGA image.\n");
        return;
    }
    print_stat("Stats window cycles: ", stats[0], 0);
    if (stats_version >= 2) {
        print_stat("Retired instructions: ", retired_instructions, 0);
        if (!(stats[7] & 0x81) && stats[0] && retired_instructions) {
            print_ratio("IPC                : ", retired_instructions, stats[0]);
            print_ratio("CPI                : ", stats[0], retired_instructions);
        } else {
            xprintf("IPC/CPI unavailable: zero denominator or counter overflow.\n");
        }
    } else {
        xprintf("IPC/CPI unavailable: requires statistics v2 FPGA image.\n");
    }
    print_stat("IF request wait    : ", stats[1], 1);
    print_stat("IF input bubbles   : ", stats[2], 1);
    print_stat("Memory stall cycles: ", stats[3], 1);
    print_stat("Mul/div stall cycles: ", stats[4], 1);
    print_stat("BJP redirects      : ", stats[5], 0);
    print_stat("BJP instructions   : ", stats[6], 0);
    xprintf("Stats overflow mask: 0x%02lx\n", (unsigned long)stats[7]);
    xprintf("Event counters may overlap; BJP counts include JAL/JALR.\n");
    xprintf("IF bubbles include refill; redirects are events, not penalty cycles.\n");
    if (stats_version >= 2)
        xprintf("IPC/CPI use retired instructions and cycles from the same stats window.\n");
}
