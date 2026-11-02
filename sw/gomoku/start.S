.section .text.start
.globl _start
_start:
 .option push
 .option norelax
 la sp,__stack_top
 .option pop
 la t0,__data_load
 la t1,__data_start
 la t2,__data_end
1: bgeu t1,t2,2f
 lbu t3,0(t0)
 sb t3,0(t1)
 addi t0,t0,1
 addi t1,t1,1
 j 1b
2: la t0,__bss_start
 la t1,__bss_end
3: bgeu t0,t1,4f
 sw zero,0(t0)
 addi t0,t0,4
 j 3b
4: la t0,trap
 csrw mtvec,t0
 li a0,0
 li a1,0
 call main
 li t0,0x20003000
 sw a0,0(t0)
5: j 5b
.balign 4
trap:
 csrr t1,mcause
 li t0,0x20003000
 lui t2,0xdead0
 or t1,t1,t2
 sw t1,0(t0)
 j trap
