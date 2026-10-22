.section .text.start
.globl _start
_start:
 li x1,0x80000001
 li x2,0xffff0001
 li x28,0x10000000
 li x3,0
 li x4,48
 li x14,0
loop:
 mul x10,x1,x2
 mulh x11,x1,x2
 mulhsu x12,x1,x2
 mulhu x13,x1,x2
 addi x14,x14,1
 add x15,x10,x11
 mul x16,x15,x2
 add x17,x16,x12
 sw x17,0(x28)
 lw x18,0(x28)
 mul x24,x1,x2
 mul x19,x18,x1
 mul x0,x1,x2
 mul x20,x1,x2
 mul x20,x2,x2
 add x21,x20,x2
 mul x22,x1,x2
 beq x0,x0,keep_older
 addi x22,x0,0
keep_older:
 add x23,x22,x21
 sw x23,4(x28)
 addi x1,x1,123
 addi x2,x2,-97
 addi x3,x3,1
 blt x3,x4,loop
 li x28,0x20003000
 li x29,1
 sw x29,0(x28)
done: j done
