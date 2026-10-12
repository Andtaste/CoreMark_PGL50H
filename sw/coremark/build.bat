@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 exit /b 1
rem If PATH is unavailable, set RISCV_TOOLCHAIN_BIN to the installed bin folder.
if defined RISCV_TOOLCHAIN_BIN set "PATH=%RISCV_TOOLCHAIN_BIN%;%PATH%"
for %%T in (gcc objcopy objdump size) do (
  where riscv-none-elf-%%T >nul 2>nul
  if errorlevel 1 (
    echo ERROR: riscv-none-elf-%%T not found. Check PATH.
    exit /b 1
  )
)
set "COPT=-O2 -mcmodel=medlow"
set "ISA=-march=rv32im_zicsr -mabi=ilp32"
set "SECT=-ffunction-sections -fdata-sections"
set "LIB=-fno-builtin-printf -fno-builtin-malloc"
rem All memory addresses and capacities come from ..\link.lds.
riscv-none-elf-gcc %COPT% %ISA% %SECT% %LIB% -DITERATIONS=2000 ^
  -I. -I.. -I..\include ^
  core_list_join.c core_main.c core_matrix.c core_state.c core_util.c core_portme.c ^
  ..\start.S ..\trap_entry.S ..\init.c ..\trap_handler.c ^
  ..\lib\utils.c ..\lib\xprintf.c ..\lib\uart.c ^
  -T ..\link.lds -nostartfiles -Wl,--gc-sections -Wl,--check-sections ^
  -Wl,-Map,coremark.map -o coremark.elf
if errorlevel 1 goto :fail
riscv-none-elf-objcopy -O binary coremark.elf coremark.bin
if errorlevel 1 goto :fail
riscv-none-elf-objdump --disassemble-all coremark.elf > coremark.dump
if errorlevel 1 goto :fail
riscv-none-elf-size coremark.elf
if errorlevel 1 goto :fail
echo BUILD_OK: coremark.elf coremark.bin coremark.dump coremark.map
echo Confirm board memory, UART and clock settings before downloading.
exit /b 0
:fail
echo BUILD_FAILED. Do not download an old BIN from a previous build.
exit /b 1
