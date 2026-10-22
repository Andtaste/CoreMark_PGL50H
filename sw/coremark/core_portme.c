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
static uint32_t secondary_retired;
static uint32_t loads,stores,operand_wait,id_blocked;

/* Reporting only: explicit unsigned long division keeps formatting independent
 * of RV32 libgcc's multiply/divide based 64-bit division implementation. */
static uint64_t report_divmod(uint64_t n, uint64_t d, uint64_t *remainder)
{
    uint64_t q = 0, r = 0;
    unsigned i;
    for (i = 0; i < 64; ++i) {
        unsigned carry = (unsigned)(r >> 63);
        r = (r << 1) | (n >> 63);
        n <<= 1;
        q <<= 1;
        if (carry || r >= d) { r -= d; q |= 1; }
    }
    if (remainder) *remainder = r;
    return q;
}

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
        uint64_t digit;
        value = report_divmod(value, 10, &digit);
        *--cursor = '0' + (unsigned)digit;
    } while (value);
    xprintf("%s%s", label, cursor);
}

/* Print quotient then decimal digits, without numerator*1000 overflow.
 * Repeated modular addition also avoids overflow in remainder*10. */
static void write_fixed(uint64_t n, uint64_t d, unsigned digits)
{
    uint64_t remainder, whole;
    unsigned i;
    if (!d) { xputs("unavailable"); return; }
    whole = report_divmod(n, d, &remainder);
    print_u64("", whole);
    xputc('.');
    for (i = 0; i < digits; ++i) {
        uint64_t acc = 0;
        unsigned digit = 0, j;
        for (j = 0; j < 10; ++j) {
            if (acc >= d - remainder) { acc -= d - remainder; ++digit; }
            else acc += remainder;
        }
        xputc('0' + digit);
        remainder = acc;
    }
}

static void print_fixed(const char *label, uint64_t n, uint64_t d, unsigned digits)
{
    xputs(label);
    write_fixed(n, d, digits);
    xputc('\n');
}

static void print_stat(const char *label, uint32_t value, int cycles)
{
    xprintf("%s%lu", label, (unsigned long)value);
    if (cycles && stats[0] && !stats[7]) {
        xputs(" (");
        write_fixed((uint64_t)value * 100, stats[0], 3);
        xputs("%)");
    }
    xputc('\n');
}

/* Fixed-point ratios avoid floating-point printf support on RV32. */
static void print_ratio(const char *label, uint32_t numerator, uint32_t denominator)
{
    print_fixed(label, numerator, denominator, 3);
}

static void print_secondary_stats(void)
{
    print_stat("Secondary retired  : ", secondary_retired, 0);
    if (!stats[7] && stats[0] && secondary_retired <= stats[0]) {
        xputs("Secondary slot use : ");
        write_fixed((uint64_t)secondary_retired * 100, stats[0], 3);
        xputs("%\n");
    } else {
        xputs("Secondary slot use : unavailable (zero, overflow or invalid count)\n");
    }
}

void portable_print_timing(CORE_TICKS ticks, ee_u32 iterations)
{
    uint64_t total_iterations = (uint64_t)iterations * default_num_contexts;
    print_u64("Total ticks      : ", ticks); xputc('\n');
    print_fixed("Total time (secs): ", ticks, CPU_FREQ_HZ, 6);
    print_fixed("Iterations/Sec   : ", total_iterations * CPU_FREQ_HZ, ticks, 6);
    print_fixed("CoreMark/MHz     : ", total_iterations * 1000000, ticks, 6);
    xprintf("Score status     : %s\n", ticks >= (uint64_t)CPU_FREQ_HZ * 10 ?
            "duration >= 10 s; see CRC validation below" : "short run; diagnostic only");
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
      if (stats_version >= 3) secondary_retired = STAT_READ(0x7ca);
      loads=STAT_READ(0x7cb); stores=STAT_READ(0x7cc);
      operand_wait=STAT_READ(0x7cd); id_blocked=STAT_READ(0x7ce);
  }
}

CORE_TICKS get_time(void)
{
  return t1 - t0;
}

secs_ret time_in_secs(CORE_TICKS ticks)
{
  /* HAS_FLOAT=0: integer seconds are used only by calibration/validation.
   * Printed scores use the full cycle count in portable_print_timing(). */
  return (secs_ret)report_divmod(ticks, CPU_FREQ_HZ, NULL);
}

void portable_init(core_portable *p, int *argc, char *argv[])
{
    uint32_t signature;
    uart_init();
    xprintf("\nRun configuration\n");
    xprintf("Configured CPU Hz  : %lu\n", (unsigned long)CPU_FREQ_HZ);
    xprintf("Software build     : %s %s\n", __DATE__, __TIME__);
    xprintf("Report format      : 3 (integer fixed point)\n");
    signature = STAT_READ(0x7cf);
    xprintf("Stats ABI signature: 0x%08lx\n", (unsigned long)signature);
    stats_version = signature == 0x4e430004 ? 4 :
                    signature == 0x53544103 ? 3 :
                    signature == 0x53544102 ? 2 :
                    signature == 0x53544101 ? 1 : 0;
    stats_present = stats_version != 0;
}

void portable_fini(core_portable *p)
{
    (void)p;
    xprintf("\nCPU statistics v%d\n", stats_present ? stats_version : 2);
    print_u64("Benchmark cycles64 : ", t1 - t0); xputc('\n');
    if (!stats_present) {
        xprintf("Stats CSR unavailable: rebuild/download the new FPGA image.\n");
        return;
    }
    print_stat("Stats window cycles: ", stats[0], 0);
    if (stats_version >= 2) {
        print_stat("Retired instructions: ", retired_instructions, 0);
        if (!stats[7] && stats[0] && retired_instructions &&
            (uint64_t)retired_instructions <= (uint64_t)stats[0] * 2) {
            print_ratio("IPC                : ", retired_instructions, stats[0]);
            print_ratio("CPI                : ", stats[0], retired_instructions);
            xprintf("Counter bounds     : PASS (retired <= 2*cycles)\n");
        } else {
            xprintf("IPC/CPI unavailable: zero, overflow or retired > 2*cycles.\n");
        }
    } else {
        xprintf("IPC/CPI unavailable: requires statistics v2 FPGA image.\n");
    }
    if (stats_version >= 3) print_secondary_stats();
    print_stat("Retired loads      : ", loads, 0);
    print_stat("Retired stores     : ", stores, 0);
    print_stat("EX operand wait    : ", operand_wait, 1);
    print_stat("ID blocked cycles  : ", id_blocked, 1);
    print_stat("IF request wait    : ", stats[1], 1);
    print_stat("IF queue empty     : ", stats[2], 1);
    print_stat("MEM occupied cycles: ", stats[3], 1);
    print_stat("Mul/div stall cycles: ", stats[4], 1);
    print_stat("BJP redirects      : ", stats[5], 0);
    print_stat("BJP instructions   : ", stats[6], 0);
    if (!stats[7] && stats[6] && stats[5] <= stats[6])
        print_fixed("BJP redirect rate %: ", (uint64_t)stats[5] * 100, stats[6], 3);
    else xprintf("BJP redirect rate  : unavailable\n");
    if (stats_version >= 3)
        xprintf("Stats overflow mask: 0x%04lx\n", (unsigned long)stats[7]);
    else xprintf("Stats overflow mask: 0x%02lx\n", (unsigned long)stats[7]);
    xprintf("Event counters may overlap; BJP counts include JAL/JALR.\n");
    xprintf("IF bubbles include refill; redirects are events, not penalty cycles.\n");
    xprintf("BJP redirects count prediction corrections, jumps and stale predictions.\n");
    if (stats_version >= 2)
        xprintf("IPC/CPI use retired instructions and cycles from the same stats window.\n");
    uart_drain();
}
