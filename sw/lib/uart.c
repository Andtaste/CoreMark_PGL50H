#include <stdint.h>
#include "../include/uart.h"
#include "../include/xprintf.h"
void uart_putc(uint8_t c) {
    while (!(UART0_REG(UART0_STATUS) & 1)) {}
    UART0_REG(UART0_TXDATA) = c;
}
void uart_drain(void) { while (!(UART0_REG(UART0_STATUS) & 1)) {} }
void uart_init(void) { xdev_out(uart_putc); }
