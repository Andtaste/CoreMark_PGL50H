#include <stdint.h>

#include "../include/utils.h"



uint64_t get_cycle_value()
{
    uint32_t hi, lo, hi_again;
    do {
        hi = read_csr(cycleh);
        lo = read_csr(cycle);
        hi_again = read_csr(cycleh);
    } while (hi != hi_again);
    return ((uint64_t)hi << 32) | lo;
}

void busy_wait(uint32_t us)
{
    uint64_t tmp;
    uint32_t count;

    count = us * CPU_FREQ_MHZ;
    tmp = get_cycle_value();

    while (get_cycle_value() < (tmp + count));
}
