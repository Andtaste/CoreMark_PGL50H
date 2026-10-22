.section .text.start
.globl _start
_start:
 la x5,handler
 csrw mtvec,x5
 li x1,0x80000001
 li x2,0xffff0001
 li x20,123
 li x21,456
 li x28,0x20003000
 li x29,2
 li x6,0x30000000
 lw x7,0(x6)
 mul x20,x1,x2
 mulh x21,x1,x2
 sw x29,0(x28)
after_fault:
 li x8,123
 bne x20,x8,fail
 li x8,456
 bne x21,x8,fail
 li x29,1
 sw x29,0(x28)
done: j done
handler:
 csrr x8,mcause
 li x9,5
 bne x8,x9,fail
 csrr x8,mtval
 bne x8,x6,fail
 la x8,after_fault
 csrw mepc,x8
 mret
fail:
 li x29,2
 sw x29,0(x28)
 j fail
