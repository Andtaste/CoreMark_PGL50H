OUTPUT_ARCH(riscv)
ENTRY(_start)
MEMORY { CODE (rwx) : ORIGIN = 0, LENGTH = 96K
         DATA (rw) : ORIGIN = 0x10000000, LENGTH = 128K }
SECTIONS {
 /* Keep game code/tables low; keep CoreMark constants in their separate high region. */
 .text : { KEEP(*(.text.start))
  *(EXCLUDE_FILE (*cm_*.o) .text*)
  *(EXCLUDE_FILE (*cm_*.o) .rodata*)
  *(.text*) *(.rodata*) } > CODE
 /* Prioritize hot board/move state in the existing low-32KiB fast region. */
 .hot_bss (NOLOAD) : { . = ALIGN(4); __hot_bss_start = .; *(.position_bss) . = ALIGN(4); __hot_bss_end = .; } > DATA
 /* History stays contiguous in BRAM; its prefix shares the fast window. */
 .history (NOLOAD) : { __history_start = .; KEEP(*(.history)) __history_end = .; } > DATA
 .data : { . = ALIGN(4); __data_start = .; *(.sdata*) *(.data*) __data_end = .; } > DATA AT> CODE
 __data_load = LOADADDR(.data);
 .bss (NOLOAD) : { . = ALIGN(4); __bss_start = .; *(.zobrist_bss) *(.sbss*) *(.bss*) *(COMMON) . = ALIGN(4); __bss_end = .; } > DATA
 __stack_top = ORIGIN(DATA) + LENGTH(DATA);
 ASSERT(__history_end - __history_start == 32400, "history must be 90x90 int32")
 ASSERT(__hot_bss_start == 0x10000000, "attack snoop board base changed")
 ASSERT(__hot_bss_end <= 0x10008000, "hot board state escaped fast BRAM")
 ASSERT(__bss_end <= __stack_top - 49152, "insufficient search stack")
}
