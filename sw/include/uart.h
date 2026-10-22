#ifndef NC_UART_H
#define NC_UART_H
#include <stdint.h>
#define UART0_TXDATA 0x20000000u
#define UART0_STATUS 0x20000004u
#define UART0_REG(addr) (*(volatile uint32_t *)(addr))
void uart_init(void);
void uart_putc(uint8_t c);
void uart_drain(void);
#endif
