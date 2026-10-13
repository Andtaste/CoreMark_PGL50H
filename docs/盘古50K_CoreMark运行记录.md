# 盘古50K运行CoreMark：操作记录与复现说明

记录日期：2026-10-13。依据当前工程文件与已收到的串口输出整理。

## 1. 本次实现及当前状态

在盘古50K MES50HP上运行TinyRISC-V裸机CoreMark，采用“程序预置到FPGA片内RAM初始化内容”的方案：

```text
CoreMark C源码 → RISC-V GCC → coremark.elf → coremark.bin
→ coremark_init.dat → ram1初始化 → PDS生成top.sbit
→ FPGA配置JTAG临时下载 → CPU执行 → UART输出 → PuTTY接收
```

本次没有运行FreeRTOS，没有通过OpenOCD/GDB向CPU单独下载程序，也没有烧写SPI Flash。FPGA通过Boundary Scan临时配置，断电后需要重新下载top.sbit。

已确认：工具链可执行；三个IP已生成并加入工程；PDS已生成配置文件；板上能执行CoreMark并通过UART输出。

尚未确认：有效的正式CoreMark性能成绩。最新收到的日志仍显示`Iterations : 10`、`Total ticks : 5951005`及运行不足10秒错误。当前编译脚本已经设为2000次，但尚未收到2000次运行的板上结果。不能把“已有串口输出”记为“性能测试全部通过”。

## 2. 板卡、软件与目录

| 项目 | 本次使用值 |
|---|---|
| 核心板 | MES50HP V1.0，盘古50K |
| 底板 | Mespro_Base_Board V1.1 |
| FPGA | PGL50H，FBG484，速度等级-6；芯片标识PGL50H-6IFBG484 |
| FPGA开发软件 | Pango Design Suite 2022.2-SP1-Lite |
| 软件工具链 | xPack GNU RISC-V Embedded GCC 15.2.0，Windows x64 |
| 工具前缀 | riscv-none-elf-（与参考指南riscv32-unknown-elf-前缀不同） |
| UART桥接芯片 | CP2102 |
| 串口终端 | PuTTY |
| 本机已识别端口 | COM13；换电脑或USB口后以设备管理器为准 |

工程根目录：`C:\Users\Lenovo\Desktop\FPGA\CoreMark_PGL50H`。下文短路径均相对此目录。

```text
CoreMark_PGL50H/
├─ hardware/
│  └─ pds/
│     ├─ CoreMark_PGL50H.pds
│     ├─ source/
│     │  ├─ source/top.v       板级顶层
│     │  ├─ top/              SoC顶层
│     │  ├─ core/             CPU、defines.v等
│     │  ├─ perips/           rom.v、ram.v、UART等
│     │  ├─ debug/            CPU调试模块
│     │  └─ utils/            公共RTL
│     ├─ ipcore/{pll,ram1,ram2}/
│     └─ generate_bitstream/top.sbit
├─ sw/
│  ├─ coremark/               C源码、build.bat、ELF/BIN/DAT等
│  ├─ include/                utils.h、uart.h等
│  ├─ lib/                    utils.c、uart.c、xprintf.c等
│  ├─ start.S、trap_entry.S、init.c、trap_handler.c
│  └─ link.lds
├─ docs/                      本记录
├─ simulation/
├─ tools/
├─ output/
└─ logs/
```

当前PDS工程仍引用工程外的约束文件：

`C:\Users\Lenovo\Desktop\progject\FPGA_Competition-RISC-V_Processor-in-PGL22G-main\tinydram.fdc`

此FDC已按本板修改。复制工程到别处时必须同时带上它并在PDS重新指定路径；ram1初始化文件使用绝对路径，也要重新选择。仅复制CoreMark_PGL50H文件夹不能保证路径完整。

## 3. 软件程序的准备

### 3.1 工具链

从[xPack RISC-V GCC发布页](https://github.com/xpack-dev-tools/riscv-none-elf-gcc-xpack/releases)取得Windows x64压缩包并解压，本次使用15.2.0-1。将包含gcc.exe的bin目录加入Windows用户变量Path。工具链放在工程外即可。

本机目录为：

```text
D:\Program Files\riscv\xpack-riscv-none-elf-gcc-15.2.0-1-win32-x64\xpack-riscv-none-elf-gcc-15.2.0-1\bin
```

新开命令窗口，执行以下命令确认PATH已生效：

```bat
riscv-none-elf-gcc --version
riscv-none-elf-objcopy --version
riscv-none-elf-objdump --version
riscv-none-elf-gdb --version
```

本方案使用gcc编译链接、objcopy导出BIN、objdump导出反汇编、size查看大小。GDB已安装，本次运行过程没有使用。

### 3.2 软件地址和编译

`sw/link.lds`规定：程序区起点`0x00000000`，64KiB；数据RAM起点`0x10000000`，32KiB。链接脚本中的`flash`只是程序区名称，在本方案中对应片内ram1，并不表示已经烧写板上SPI Flash。

`sw/include/utils.h`的CPU频率为50MHz，与PLL输出及RTL频率宏一致。保留原UART驱动、启动程序和CoreMark计算代码。

在资源管理器打开`sw/coremark`，地址栏输入`cmd`并回车，然后执行：

```bat
build.bat
```

当前编译使用`-O2 -mcmodel=medlow -march=rv32im_zicsr -mabi=ilp32`，以及段回收选项。当前命令带`-DITERATIONS=2000`。`core_portme.h`仅在ITERATIONS未定义时默认取10，所以命令行2000会生效，无须把默认定义再改一遍。

出现`BUILD_OK`才使用本次产物：`coremark.elf`、`coremark.bin`、`coremark.dump`、`coremark.map`。编译失败时不得继续用残留BIN生成初始化文件。

### 3.3 BIN转RAM初始化文件

在`sw/coremark`目录打开PowerShell，完整执行下列脚本。结果是ASCII格式、16384行、每行8个十六进制字符的`coremark_init.dat`。BIN按小端32位字重排，不足64KiB的部分补零。

```powershell
$binPath = Join-Path $PWD.Path "coremark.bin"
$hexPath = Join-Path $PWD.Path "coremark_init.dat"
if (!(Test-Path -LiteralPath $binPath)) {
    throw "找不到 coremark.bin，请先编译成功。"
}
$programBytes = [System.IO.File]::ReadAllBytes($binPath)
if ($programBytes.Length -eq 0) { throw "coremark.bin 是空文件。" }
if ($programBytes.Length -gt 65536) { throw "程序超过 ram1 的64KiB容量。" }
$memoryBytes = New-Object byte[] 65536
[System.Array]::Copy($programBytes, 0, $memoryBytes, 0, $programBytes.Length)
$hexLines = New-Object string[] 16384
for ($wordIndex = 0; $wordIndex -lt 16384; $wordIndex++) {
    $offset = $wordIndex * 4
    $hexLines[$wordIndex] = (
        "{0:X2}{1:X2}{2:X2}{3:X2}" -f
        $memoryBytes[$offset + 3], $memoryBytes[$offset + 2],
        $memoryBytes[$offset + 1], $memoryBytes[$offset]
    )
}
[System.IO.File]::WriteAllLines($hexPath, $hexLines, [System.Text.Encoding]::ASCII)
Write-Host "转换完成：$hexPath"
Write-Host "程序大小：$($programBytes.Length) 字节"
Write-Host "初始化文件：16384行，每行8位十六进制字符"
```

须看到“转换完成”。只把脚本文本粘贴到尚未结束的多行输入中、不实际执行，不会更新文件。

## 4. FPGA工程的准备

### 4.1 工程与源文件

现有工程直接打开`hardware/pds/CoreMark_PGL50H.pds`。从零复现则在`hardware/pds`创建RTL project，器件选Logos/PGL50H/FBG484/-6，综合工具ADS，添加`hardware/pds/source`并启用包含子目录。不要添加testbench或IP实例化模板作为综合源文件。

顶层模块设为`top`，源码是`source/source/top.v`；SoC实例模块为`tinyriscv_soc_top`。在Report Summary确认`Top Module: top`。添加前述FDC文件。

### 4.2 约束与时钟

当前有效FDC的主要端口如下，适用于本次MES50HP及底板组合：

| 顶层端口 | FPGA管脚 | 用途 |
|---|---|---|
| clk | P20 | 50MHz板载时钟 |
| rst_ext_i | K18 | KEY1，低电平复位 |
| uart_tx_pin | R9 | CPU串口发送，连接板上UART桥 |
| uart_rx_pin | R8 | CPU串口接收 |
| halted_ind | B2 | LED1，CPU调试停止指示 |
| jtag_TCK / TMS / TDI / TDO | AB13 / Y13 / AB11 / Y11 | RTL的CPU调试接口，当前下载流程未使用 |
| gpio[0] / gpio[1] | W11 / V11 | GPIO |

时钟约束：`create_clock -name {sys_clk} [get_ports {clk}] -period {20.000} -waveform {0.000 10.000} -add`。当前端口VCCIO为3.3V，输出主要用LVCMOS33、输入主要用LVTTL33，保留实际FDC设置。

板上FPGA配置JTAG与表中RTL CPU调试JTAG是不同路径。本次下载器连接板上配置JTAG；没有把CoreMark通过表中四个CPU调试信号下载。

当前磁盘上的top.v仍把外部jtag_TCK/TMS/TDI接入SoC。此前讨论过内部固定为0/1/0以停用调试，但这一变更没有出现在当前文件中，不能记为已完成；未使用的调试输入须确保有确定电平，后续可另行处理。

### 4.3 三个PDS IP

通过Tools → IP Compiler生成，器件与工程一致。存储器选Module → Memory → DRM → DRM Based Single Port RAM，模块名与调用一致。把生成的`.idf`加入PDS工程。

| 设置 | pll | ram1 | ram2 |
|---|---|---|---|
| 类型 | PLL | DRM单端口RAM | DRM单端口RAM |
| 输入/输出频率 | 50MHz → 50MHz | — | — |
| Data Width | — | 32 | 32 |
| Address Width | — | 14 | 13 |
| 容量 | — | 16384字×4字节=64KiB | 8192字×4字节=32KiB |
| Byte Write | — | 开启，4×8位 | 开启，4×8位 |
| Write Mode | — | NORMAL_WRITE | TRANSPARENT_WRITE |
| Output Register | — | 关闭 | 关闭 |
| Reset Type | — | ASYNC | ASYNC |
| 初始化 | — | 开启，HEX，选择coremark_init.dat | 关闭 |

PLL采用内部反馈，仅启用clkout0，相位0°、占空比50%，端口为clkin1/pll_lock/clkout0。当前top.v声明clkin1和pll_locked，将PLL锁定信号接入复位：`.rst_ext_i(rst_ext_i & pll_locked)`。

ram1对应`source/perips/rom.v`中的`ram1 rom111`，ram2对应`ram.v`中的`ram2 ram222`。rom.v是程序存储器包装模块名，底层使用可初始化RAM。因此本方案不需要另建名为rom1的ROM IP。地址基址由SoC地址译码和链接脚本决定，IP配置的是容量与接口，不会自动为CPU分配基址。

设置初始化文件后重新Generate ram1，日志须为0 error(s)。生成模板`*_tmpl.v`供查看接口，不是要加入综合的实现模块。

### 4.4 生成配置文件

在PDS左下Flow依次运行：

```text
Compile → Synthesize → Device Map → Place & Route
→ Report Timing → Generate Bitstream
```

处理报错；在Report Summary/Timing相关报告查看50MHz时钟及PLL派生时钟、Setup/Hold裕量和未约束路径。步骤绿色勾号表示流程完成，不能单凭勾号声称全部时序满足。

本次配置文件位置：`hardware/pds/generate_bitstream/top.sbit`。不要选择`bak`目录里的旧文件。

## 5. 串口连接与PuTTY设置

### 5.1 接线和驱动

板卡接正常电源；用有数据传输功能的USB线连接底板标为**UART**的USB口，位置在DCIN-12V电源插座附近。板上CP2102把UART转为USB，不需要另接USB-TTL模块。FPGA配置JTAG下载线和UART USB线分别承担下载与接收结果的任务。

本次CP2102曾在设备管理器显示黄色警告，安装[Silicon Labs官方CP210x VCP驱动](https://www.silabs.com/software-and-tools/usb-to-uart-bridge-vcp-drivers)后，设备显示为COM13。

驱动压缩包：[CP210x Universal Windows Driver](https://www.silabs.com/documents/public/software/CP210x_Universal_Windows_Driver.zip)。下载解压后，可在设备管理器右键CP2102 → 更新驱动程序 → 浏览我的电脑以查找驱动程序 → 指定解压目录并包含子文件夹。安装后重新插拔，查看“端口（COM和LPT）”。

复现时按插拔UART USB线前后新增的端口判断，避免误选蓝牙COM口或下载器的串口。COM13是本机当时分配值，不是板卡固定编号。

### 5.2 软件与参数

使用[PuTTY官方下载页](https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html)的Windows x86 64位安装包。本次提供的是[PuTTY 0.85 MSI](https://the.earth.li/~sgtatham/putty/0.85/w64/putty-64bit-0.85-installer.msi)。安装后从开始菜单打开PuTTY。

| 位置 | 参数 | 设置 |
|---|---|---|
| Session | Connection type | Serial |
| Session | Serial line | COM13（复现者填自己的COM号） |
| Session | Speed | 115200 |
| Connection → Serial | Data bits | 8 |
| Connection → Serial | Stop bits | 1 |
| Connection → Serial | Parity | None |
| Connection → Serial | Flow control | None |
| Terminal | Implicit CR in every LF | 勾选，修正阶梯状换行 |

在Session的Saved Sessions输入`CoreMark_COM13`并Save，下次Load即可恢复设置。需要留存日志时，在Session → Logging选All session output，指定新的日志文件后Open。

点击Open出现终端窗口，表示电脑正在接收串口，不等于CPU已经运行。串口由程序初始化，通常只输出一轮结果；应先打开PuTTY，再下载FPGA或按KEY1重跑。串口窗口一直空白时，依次确认COM号、115200、下载成功及KEY1复位。COM口打开失败时，关闭占用该端口的其他串口软件。

若文本可读但每行向右错位，设置Implicit CR in every LF；若乱码，优先检查波特率和实际CPU频率。设备管理器的默认波特率不代替PuTTY中的设置。

## 6. 临时下载与运行

1. 接板卡电源、FPGA配置JTAG下载器和UART USB线，先打开PuTTY。
2. PDS菜单Tools → Configuration，打开Fabric Configuration。
3. 使用Boundary Scan，在右侧空白区右键Initialize JTAG Chain；连接下载器并识别器件。应出现Logos-PGL50H。
4. 对器件指定配置文件，选择本次生成的`generate_bitstream/top.sbit`。
5. 右键器件执行Program，确认日志显示成功。仅分配文件或Open config cable成功不表示下载完成。
6. 在PuTTY等待输出；若错过启动输出，按KEY1复位CPU，再观察。
7. 保存完整结果。不要把REPROGRAM当CPU复位键；临时配置在断电后丢失，重上电须重新下载。

本次选择Boundary Scan临时配置，不使用SPI Flash Configuration，不需要Convert File生成Flash烧录文件。CoreMark已经包含在ram1初始化中，不能把coremark.bin当top.sbit交给FPGA配置工具。

## 7. 每次更改文件后的执行流程

| 修改内容 | 必须重新执行 |
|---|---|
| CoreMark C文件、启动文件、软件库、头文件、link.lds、build.bat或迭代次数 | build.bat → BIN转DAT → Generate ram1 → PDS完整重建 → 下载新top.sbit → 复位接收 |
| 仅替换coremark_init.dat | Generate ram1 → PDS完整重建 → 下载 → 接收 |
| RTL或IP参数 | 重新生成受影响IP（如有）→ Compile/Synthesize/Map/Place & Route/Timing/Bitstream → 下载 |
| FDC管脚或时钟约束 | 从Synthesize开始重建直至Bitstream → 下载；完整重跑也可 |
| CPU频率或存储容量 | 同步修改RTL/IP、约束及软件频率/链接脚本，再走软件和硬件全流程 |
| PuTTY端口、显示或日志设置 | 重新打开串口即可，不需编译 |

更新程序时最稳妥的顺序：

```text
保存源文件
→ build.bat，确认BUILD_OK
→ 转DAT，确认“转换完成”
→ ram1重新Generate，确认0 error(s)
→ PDS从Compile开始重新执行全部实现步骤
→ 确认新top.sbit的修改时间
→ Fabric Configuration重新指定该文件并Program成功
→ 清除旧串口记录，按KEY1，看新输出
```

PDS提示“This operation will rerun this action”是在询问重新运行，点击Yes。可勾选Run from first out-of-date action自动处理过期步骤；仅DAT改变时不要只依赖自动过期判断，仍主动重新生成ram1并重建硬件。

当前脚本目标2000次，板上应显示`Iterations : 2000`。若仍为10次，逐段排查BIN、DAT、IP生成结果、bitstream和下载文件，不要只重复按复位键。修改源文件不会直接改变已下载到FPGA的程序。

## 8. 已收到结果与判定

首次及最近提供的输出包含：

```text
CoreMark Size    : 666
Total ticks      : 5951005
Total time (secs): 0
Iterations       : 10
seedcrc          : 0xe9f5
[0]crclist       : 0xe714
[0]crcmatrix     : 0x1fd7
[0]crcstate      : 0x8e3a
[0]crcfinal      : 0xfcaf
ERROR! Must execute for at least 10 secs for a valid result!
Errors detected
```

50MHz下5951005个周期约0.119秒；显示0秒不能单独判定计时失效。标题“2K performance run”与单项CoreMark Size 666同时出现，不应凭标题再额外修改工作区大小。

将迭代改为2000后按上述全流程更新，按现有速度估计约24秒，实际以新输出为准。有效结果必须满足运行至少10秒并通过CoreMark校验，保存完整日志；当前尚未取得该证据。若2000次仍报错，继续检查新日志中的具体错误及计时，不直接给出分数。

## 9. 相比原文件的实际改动

对比基准分别是`progject/FPGA_Competition-RISC-V_Processor-in-PGL22G-main/source`的RTL与`progject/tinyriscv-master/tests/example`的软件。以下依据当前磁盘文件对比，区分保留项与实际修改。

| 文件/项目 | 原内容 → 当前内容 | 目的 |
|---|---|---|
| RTL source/source/top.v（原source/top.v） | wire clkin改为明确声明clkin1；新增pll_locked；接收pll_lock；SoC复位输入改为rst_ext_i & pll_locked | 明确PLL输出网络，并等待锁定后释放CPU复位 |
| RTL source/core/defines.v | ROM_DEPTH 1024→16384；RAM_DEPTH 4096→8192 | 程序区扩展为64KiB，数据区扩展为32KiB |
| PDS工程与IP | 新建PGL50H/FBG484/-6工程，生成pll、ram1、ram2并添加.idf | 面向目标器件生成实现 |
| ram1配置 | 32位、14位地址、HEX初始化指向coremark_init.dat | 预置CoreMark程序 |
| ram2配置 | 32位、13位地址、不开启初始化 | 提供32KiB数据RAM |
| tinydram.fdc | 将原板引脚改为本板引脚 | 对接MES50HP及底板 |
| sw/link.lds | 程序区16K→64K；数据RAM16K→32K；基址不变 | 解决原编译程序区溢出，并匹配硬件容量 |
| sw/coremark/core_portme.h | FLAGS_STR改为当前编译选项；PERFORMANCE_RUN及ITERATIONS加条件定义；默认10000次→10次 | 允许编译命令覆盖宏，10次用于首次运行检查 |
| sw/coremark/build.bat | 新增Windows编译脚本；工具前缀riscv-none-elf-；PATH检查、失败终止、ELF/BIN/DUMP/MAP输出；当前-DITERATIONS=2000 | 用已安装的xPack工具链编译并更新正式运行时长 |
| sw/coremark/coremark_init.dat | 新增BIN转换产物 | 为ram1提供程序初始化内容 |
| 工程目录、说明文件 | 新建CoreMark_PGL50H框架和记录文件 | 分开管理软硬件及结果 |

原FDC管脚与本次管脚的会话记录：halted_ind U10→B2；UART TX R18→R9；clk B5→P20；reset U12→K18；UART RX N14→R8；调试TDO/TCK/TDI/TMS V16/V17/V18/T18→Y11/AB13/AB11/Y13；GPIO[1]/[0] P17/U11→V11/W11。20ns时钟约束保留。注意原FDC文件已直接被修改，当前参考目录不是这一文件的原始快照。

下列内容保留原实现，没有记为本次新增修改：

- 竞赛工程的rom.v调用ram1、ram.v调用ram2及字节写接口，当前比较未发现内容变化。
- 其他可对应的竞赛RTL文件未发现内容变化；本次没有重写CPU内核。
- TinyRISC-V软件的core_portme.c、CoreMark计算文件、utils.c、UART驱动、启动及中断相关文件当前对比未发现内容变化。
- 软件utils.h和RTL CPU_CLOCK_HZ原本就是50MHz，本次确认了匹配关系，没有改频率。
- 关闭中断、修改utils.c周期计数读取方式、内部固定JTAG输入只是此前讨论项，当前未作为已完成改动。
- sw/uart_tx/build.bat也是新增的辅助示例脚本，但本次CoreMark运行没有使用它。

## 10. 交接时需要保留的信息

交接整个工程、有效FDC及ram1初始化文件；标明路径依赖。记录PDS和工具链版本、COM号与115200/8N1/无流控设置。每次正式结果连同当次源码、迭代次数、时钟、编译选项、BIN/DAT和top.sbit一并保存，避免旧程序结果与新源码混用。

下一项待完成工作：确认2000次程序经过BIN→DAT→IP→bitstream→板卡的全链路更新，并保存满足10秒及校验要求的串口结果。
