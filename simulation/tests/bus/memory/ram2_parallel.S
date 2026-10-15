/* Current CPU directed test: ram2 accesses while fetching from ram1. */
.section .text
.global _start
_start:
    li x26, 0
    li x27, 0
    li gp, 1
    li t0, 0x10000000
    li t1, 0x12345678
    sw t1, 0(t0)
    lw t2, 0(t0)
    bne t1, t2, fail

    li gp, 2
    li t1, -1
    sb t1, 1(t0)
    lb t2, 1(t0)
    bne t1, t2, fail
    lbu t2, 1(t0)
    li t3, 255
    bne t2, t3, fail
    lw t2, 0(t0)
    li t3, 0x1234ff78
    bne t2, t3, fail

    li gp, 3
    sh t1, 2(t0)
    lh t2, 2(t0)
    bne t1, t2, fail
    lhu t2, 2(t0)
    li t3, 65535
    bne t2, t3, fail
    lw t2, 0(t0)
    li t3, 0xffffff78
    bne t2, t3, fail

    li gp, 4
    li t1, 100
    li t3, 0
1:
    sw t3, 4(t0)
    lw t2, 4(t0)
    bne t3, t2, fail
    addi t3, t3, 1
    bne t3, t1, 1b

    li gp, 5
    sw zero, 8(t0)
    beq t3, t1, 2f
    sw t1, 8(t0) /* must be flushed */
2:
    lw t2, 8(t0)
    bnez t2, fail
    li x27, 1
    li x26, 1
3:  j 3b
fail:
    li x27, 0
    li x26, 1
4:  j 4b
