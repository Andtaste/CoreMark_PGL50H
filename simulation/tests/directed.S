.section .text.start
.globl _start
_start:
 li sp,0x10008000
 la t0,handler
 csrw mtvec,t0
 li s0,0
 li s1,0
 li s2,0
 li s3,0
 li t0,0x80000000
 li t1,-1
 div t2,t0,t1
 bne t2,t0,fail
 rem t2,t0,t1
 bnez t2,fail
 divu t2,t0,zero
 bne t2,t1,fail
 remu t2,t0,zero
 bne t2,t0,fail
 srai t2,t0,31
 bne t2,t1,fail
 li t0,0x10000000
 li t1,0x123480ff
 sw t1,0(t0)
 lb t2,0(t0)
 li t3,-1
 bne t2,t3,fail
 lbu t2,0(t0)
 li t3,255
 bne t2,t3,fail
 lh t2,0(t0)
 li t3,0xffff80ff
 bne t2,t3,fail
 lhu t2,0(t0)
 li t3,0x80ff
 bne t2,t3,fail
 li t1,0x55
 sb t1,1(t0)
 lw t2,0(t0)
 li t3,0x123455ff
 bne t2,t3,fail
 // Five precise traps, handler advances mepc. Store must not reach bus.
 li s1,4
 addi s2,t0,1
 lw t2,1(t0)
 li s1,6
 sw t2,1(t0)
 li s1,5
 li s2,0x00010000
 lw t2,0(s2)
 li s1,7
 sw t2,0(s2)
 li s1,2
 li s2,-1
 .word 0xffffffff
 li s1,11
 li s2,0
 ecall
 li t0,6
 bne s0,t0,fail
 // Read-only/unknown CSR traps, including writes with rd=x0.
 li s1,2
 la t0,illegal_csr
 lw s2,0(t0)
illegal_csr:
 csrw cycle,zero
 li t0,7
 bne s0,t0,fail
 // All distinct IRQ causes. IRQ register is a testbench peripheral only.
 li t0,0x888
 csrw mie,t0
 li t0,8
 csrs mstatus,t0
 li t0,0x20004000
 li t1,1
 sw t1,0(t0)
wait_soft: li t2,1
 bne s3,t2,wait_soft
 li t1,2
 sw t1,0(t0)
wait_timer: li t2,2
 bne s3,t2,wait_timer
 li t1,4
 sw t1,0(t0)
wait_ext: li t2,3
 bne s3,t2,wait_ext
 // Taken control flow must suppress younger writes and wrong-path traps.
 j good
 sw zero,0(zero)
 .word 0xffffffff
good:
 la t0,after_jalr
 ori t0,t0,1
 jalr ra,t0,0
 j fail
after_jalr:
 fence
 fence.i
 csrr t0,minstret
 beqz t0,fail
 li t0,0x20003000
 li t1,1
 sw t1,0(t0)
done: j done
fail:
 li t0,0x20003000
 li t1,0xdead
 sw t1,0(t0)
 j fail
.balign 4
handler:
 csrr t4,mcause
 bltz t4,interrupt
 bne t4,s1,fail
 csrr t5,mtval
 bne t5,s2,fail
 addi s0,s0,1
 csrr t4,mepc
 addi t4,t4,4
 csrw mepc,t4
 mret
interrupt:
 li t5,0x80000003
 beqz s3,check_irq
 li t5,0x80000007
 li t6,1
 beq s3,t6,check_irq
 li t5,0x8000000b
check_irq:
 bne t4,t5,fail
 addi s3,s3,1
 li t4,0x20004000
 sw zero,0(t4)
 mret
