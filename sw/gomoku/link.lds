OUTPUT_ARCH(riscv)
ENTRY(_start)
MEMORY { CODE (rwx) : ORIGIN = 0, LENGTH = 64K
         DATA (rw) : ORIGIN = 0x10000000, LENGTH = 32K }
SECTIONS {
 .text : { KEEP(*(.text.start)) *(.text*) *(.rodata*) } > CODE
 .data : { __data_start = .; *(.sdata*) *(.data*) __data_end = .; } > DATA AT> CODE
 __data_load = LOADADDR(.data);
 .bss (NOLOAD) : { . = ALIGN(4); __bss_start = .; *(.sbss*) *(.bss*) *(COMMON) . = ALIGN(4); __bss_end = .; } > DATA
 __stack_top = ORIGIN(DATA) + LENGTH(DATA);
 ASSERT(__bss_end <= __stack_top - 8192, "insufficient stack")
}
