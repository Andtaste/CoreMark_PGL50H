.section .text.start
.globl _start
_start:
 la t0,handler
 csrw mtvec,t0
 li s0,0
 li s4,0
 li t6,0x20003000
 li a5,0xbad
 // An older failed load must kill a younger store already in flight.
 li s1,5
 li s2,0x00010000
 la s4,recover_load
 lw a0,0(s2)
 sw a5,0(t6)
recover_load:
 li s1,0
 la s2,bad_branch
 addi s2,s2,2
bad_branch:
 .word 0x00000163
 li s1,0
 la s2,bad_jalr
 addi s2,s2,2
bad_jalr:
 jalr zero,s2,0
 li s1,3
 la s2,breakpoint
breakpoint:
 ebreak
 // Bad executable region traps at the target, not the jumping instruction.
 li s1,1
 li s2,0x40000000
 la s4,recover_fetch
 jalr zero,s2,0
recover_fetch:
 // Strict upper bound for RAM2 (no silent alias to 0x10000000).
 li s1,7
 li s2,0x10008000
 sw a5,0(s2)
 // Real FENCE.I test: overwrite a possibly-prefetched following instruction.
 la t0,patched
 li t1,0x02a00393
 sw t1,0(t0)
 fence.i
patched:
 addi t2,zero,0
 li t3,42
 bne t2,t3,fail
 // No wrong-path peripheral write.
 j next
 sw a5,0(t6)
next:
 li t0,6
 bne s0,t0,fail
 // Exercise actual timer MMIO and vectored interrupt entry.
 la t0,vectors
 ori t0,t0,1
 csrw mtvec,t0
 li s3,0
 li t0,0x20001000
 lw t1,0(t0)
 addi t1,t1,200
 sw t1,8(t0)
 sw zero,12(t0)
 li t1,128
 csrw mie,t1
 li t1,8
 csrs mstatus,t1
wait_irq:
 beqz s3,wait_irq
 li t0,1
 sw t0,0(t6)
end: j end
fail:
 sw a5,0(t6)
 j fail
.balign 4
handler:
 csrr t4,mcause
 bltz t4,irq
 bne t4,s1,fail
 csrr t5,mtval
 bne t5,s2,fail
 addi s0,s0,1
 beqz s4,normal_return
 csrw mepc,s4
 li s4,0
 mret
normal_return:
 csrr t4,mepc
 addi t4,t4,4
 csrw mepc,t4
 mret
irq:
 li t5,0x80000007
 bne t4,t5,fail
 li t4,0x20001000
 li t5,-1
 sw t5,12(t4)
 sw t5,8(t4)
 li s3,1
 mret
.balign 128
vectors:
 .rept 12
 j handler
 .endr
