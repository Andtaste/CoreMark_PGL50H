/* Five-stage forwarding, precise traps, CSR serialization and timer IRQ. */
.option norvc
.option norelax
.section .text
.globl _start
_start:
    li x26,0
    li x27,0
    li gp,1
    li t4,0x10000000
    li a0,7
    addi a0,a0,3
    add a1,a0,a0
    add a2,a1,a0
    li a3,30
    bne a2,a3,fail
    sw a2,0(t4)
    lw a4,0(t4)
    add a5,a4,a4
    li a3,60
    bne a5,a3,fail
    /* A producer retires while EX is blocked by an unrelated load. */
    li a0,11
    lw a1,0(t4)
    add a2,a0,a0
    li a3,22
    bne a2,a3,fail
    sw a2,4(t4)
    lw a4,4(t4)
    bne a4,a3,fail
    li a0,-17
    li a1,5
    mul a2,a0,a1
    li a3,-85
    bne a2,a3,fail
    div a2,a0,a1
    li a3,-3
    bne a2,a3,fail
    rem a2,a0,a1
    li a3,-2
    bne a2,a3,fail
    li gp,2
    li a0,0x12345678
    csrw mscratch,a0
    csrr a1,mscratch
    bne a0,a1,fail
    csrrwi a2,mscratch,3
    bne a0,a2,fail
    csrrsi a3,mscratch,4
    li a4,3
    bne a3,a4,fail
    csrr a3,mscratch
    li a4,7
    bne a3,a4,fail
    li gp,3
    la t0,handler
    csrw mtvec,t0
    li s0,0
    li s5,0
    sw zero,16(t4)
    li s1,11
    la s2,after_ecall
    la s3,fault_ecall
fault_ecall:
    ecall
    sw a0,16(t4)             /* Must be squashed; handler skips it. */
after_ecall:
    li s1,2
    la s2,after_illegal
    la s3,fault_illegal
fault_illegal:
    .word 0xffffffff
    sw a0,16(t4)
after_illegal:
    li s1,4
    la s2,after_load
    la s3,fault_load
fault_load:
    lw a1,1(t4)
    sw a0,16(t4)
after_load:
    li s1,6
    la s2,after_store
    la s3,fault_store
fault_store:
    sw a0,2(t4)
    sw a0,16(t4)
after_store:
    li s1,0
    la s2,after_jump
    la s3,fault_jump
    la t0,after_jump
    ori t0,t0,2
fault_jump:
    jalr zero,t0,0
    sw a0,16(t4)
after_jump:
    li s1,5
    la s2,after_access
    la s3,fault_access
    li t0,0x60000000
fault_access:
    lw a1,0(t0)
    sw a0,16(t4)
after_access:
    li s1,1
    la s2,after_fetch
    li s3,0x60000000
    jalr zero,s3,0
    sw a0,16(t4)
after_fetch:
    lw a1,16(t4)
    bnez a1,fail
    li a1,7
    bne s0,a1,fail
    /* Interrupt remains pending until all older instructions have retired. */
    li gp,4
    li t0,0x20000000
    li t1,200
    sw t1,8(t0)
    li t1,128
    csrw mie,t1
    csrsi mstatus,8
    li t1,3
    sw t1,0(t0)
wait_irq:
    beqz s5,wait_irq
    li a1,1
    bne s5,a1,fail
    li x27,1
    li x26,1
done:
    j done
handler:
    csrr t0,mcause
    bltz t0,irq_handler
    bne t0,s1,fail
    csrr t1,mepc
    bne t1,s3,fail
    csrr t2,mstatus
    andi t2,t2,8
    bnez t2,fail
    addi s0,s0,1
    csrw mepc,s2
    mret
irq_handler:
    li t1,0x80000007
    bne t0,t1,fail
    li t0,0x20000000
    li t1,4
    sw t1,0(t0)
    addi s5,s5,1
    mret
fail:
    li x27,0
    li x26,1
    j fail
