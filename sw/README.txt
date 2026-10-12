sw 软件目录使用说明
===================

依据：主目录 CoreMark_PGL50H_逐步操作教程.pdf。
来源：C:\Users\Lenovo\Desktop\progject\tinyriscv-master\tests\example。
本目录已填入参考源码及可用的 Windows 编译脚本；尚未完成目标板硬件参数确认。

目录结构
sw/
  coremark/     CoreMark 源码、平台端口、Makefile、build.bat
  uart_tx/      Hello world 串口验证例程、Makefile、build.bat
  include/      UART、CPU频率、打印及原例程配套头文件
  lib/          UART、cycle计时、打印，以及原 common.mk 的 SPI/Flash 依赖
  start.S       复位入口、栈和数据初始化
  trap_entry.S  异常入口
  init.c        CPU初始化
  trap_handler.c 异常处理
  link.lds      内存与栈的链接布局（仍是参考工程参数）
  common.mk     GNU Make 公共规则（已改为 riscv-none-elf-*）
  待修改清单.txt 目标板必须核对的配置
  SOURCE_MANIFEST.txt 来源、内容哈希和改动标记
  LICENSE.tinyriscv 原仓库许可；源文件自身的许可声明也保留

先做什么
1. 阅读“待修改清单.txt”，按实际 SoC 确认链接内存、UART 和 CPU 时钟。
2. 在资源管理器打开 sw\uart_tx，在地址栏输入 cmd，执行 build.bat。
   成功生成 uart_tx.elf/.bin/.dump/.map；下载后应输出 hello world。
3. 串口正常后，在 sw\coremark 同样执行 build.bat。
   默认 ITERATIONS=10，仅做启动检查，不能作为正式 CoreMark 成绩。
4. 正式测试前修改 coremark\core_portme.h 的 ITERATIONS，重新编译和下载。
   10000 是原仓库参考值，正式运行需满足基准要求的运行时长（至少10秒）。
5. coremark.elf/.bin/.dump/.map 先生成在 coremark 目录。
   保存成绩时把产物及构建参数复制到主目录 output/bringup 或 output/release。

工具链
脚本从 PATH 调用你已安装的 riscv-none-elf-gcc/objcopy/objdump/size。
如果新终端 PATH 尚未生效，关闭终端后重开。
也可在 CMD 中先执行：
set "RISCV_TOOLCHAIN_BIN=D:\Program Files\riscv\xpack-riscv-none-elf-gcc-15.2.0-1-win32-x64\xpack-riscv-none-elf-gcc-15.2.0-1\bin"
再执行 build.bat。编译脚本无需 GNU Make。

可选 GNU Make
有 GNU Make 和其配套 shell 工具时，可在 coremark 目录执行 make。
make ITERATIONS=10000 可覆盖 Makefile 的默认10次迭代。
原 Make 规则的 ELF 名是 coremark（无扩展名），BIN 为 coremark.bin；
build.bat 的 ELF 名是 coremark.elf。不要混淆两套输出。
本地 coremark.h 的宏现在允许命令行覆盖，避免宏重复定义。

文件归属
Verilog、FDC、PDS IP 放 hardware；OpenOCD cfg 和工具放 tools；
它们不属于 sw。GCC 工具链继续留在安装目录，也不用搬进 sw。
