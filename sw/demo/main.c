#include <stdint.h>
#define REG(a) (*(volatile uint32_t *)(a))
static void putc_uart(char c) {
    while (!(REG(0x20000004)&1)) {}
    REG(0x20000000)=(unsigned char)c;
}
static uint32_t data[128];
int main(void) {
    uint32_t sum=0;
    for (unsigned i=0;i<128;i++) data[i]=i*17+3;
    for (unsigned i=0;i<128;i++) sum+=data[i];
    if(sum!=138560) return 0xbad;
    const char *p="new_core RV32IM PASS\r\n";
    while(*p) putc_uart(*p++);
    while (!(REG(0x20000004)&1)) {}
    REG(0x20002000)=3;
    return 1;
}
