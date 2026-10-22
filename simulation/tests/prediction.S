.section .text.start
.globl _start
_start:
 li x28,0x10000000
 li x10,0
 li x11,0
 li x12,80
pattern:
 andi x13,x11,1
 beq x13,x0,even
 addi x10,x10,3
 j joined
even:
 addi x10,x10,5
joined:
 la x14,func_a
 beq x13,x0,selected
 la x14,func_b
selected:
 jalr x31,0(x14)
 addi x11,x11,1
 blt x11,x12,pattern
 beq x0,x0,1f
1:
 jal x0,2f
2:
 la x14,3f
 jalr x0,0(x14)
3:
 li x15,12
warm:
 jal x31,patch_site
 addi x15,x15,-1
 bne x15,x0,warm
 la x14,patch_site
 li x13,0x00750513
 sw x13,0(x14)
 fence.i
 jal x31,patch_site
 li x13,498
 bne x10,x13,fail
 sw x10,0(x28)
 li x28,0x20003000
 li x29,1
 sw x29,0(x28)
done: j done
fail:
 li x28,0x20003000
 li x29,2
 sw x29,0(x28)
 j fail
.balign 256
func_a:
 addi x10,x10,1
 jalr x0,0(x31)
.balign 256
func_b:
 addi x10,x10,3
 jalr x0,0(x31)
.balign 256
patch_site:
 j patch_skip
 addi x10,x10,11
patch_skip:
 jalr x0,0(x31)
