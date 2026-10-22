.section .text.start
.globl _start
_start:
 li x1,0
 .rept 256
 addi x1,x1,1
 .endr
 li x2,256
 bne x1,x2,fail
 li x28,0x20003000
 li x29,1
 sw x29,0(x28)
end: j end
fail:
 li x28,0x20003000
 li x29,0xbad
 sw x29,0(x28)
 j fail
