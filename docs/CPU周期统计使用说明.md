# CPU 周期统计

## 2026-10-15：v2 退休指令数、IPC 与 CPI

五级流水线已具有可靠的 `wb_commit = wb_valid && !wb_exception`，
新增一个 32 位饱和计数器，在与原周期计数相同的启停窗口内记录 WB 退休事件。
存储、分支、NOP、写 x0 的合法指令都计数；异常指令、气泡和被冲刷指令不计数。
若窗口内发生中断，处理程序正常退休的指令也计入，不能据此区分程序和处理程序。

- `0x7C9`：退休指令数，只读；`0x7C8[7]`：该计数器的饱和溢出标志。
- `0x7CF`：接口标识更新为 `0x53544102`；原有计数器地址和控制语义保留。
- `IPC = 退休指令数 / Stats window cycles`。
- `CPI = Stats window cycles / 退休指令数`。
- 软件用 64 位整数中间值计算，截断显示三位小数；相关计数溢出或分母为零时提示不可用。
- 比值在冻结后计算和输出，不把串口打印开销计入统计。

原有 CoreMark 结果和统计条目保留，新增条目示意如下（不是实测数据）：

```text
CPU statistics v2
Benchmark cycles64 : ...
Stats window cycles: ...
Retired instructions: ...
IPC                : 0.xxx
CPI                : x.xxx
```

统计窗口包含计时读取等边界开销，与 `Benchmark cycles64` 略有差别；
IPC 的分母使用同窗口的 `Stats window cycles`，不能混用这两个周期值。
32 位周期计数在 65 MHz 下约 66.1 秒达到饱和值，超长测量应缩短窗口。

新版软件可识别 v1 硬件并保留旧统计，提示 IPC/CPI 需要 v2 FPGA 镜像。
使用 v2 需要重新构建 CoreMark、生成 RAM 初始化文件、重新生成 ram1，
并完整实现及下载包含新 RTL 的 FPGA 镜像；仅更新软件不足以增加硬件计数器。
本次尚未运行仿真、软件构建或 PDS 实现，资源与时序影响待实现报告确认。

## 以下为 v1 首次接入记录

> 本文保留最初接入时的操作记录。当前五级内核的事件口径和后续时序调整见
> [微架构变更记录](微架构变更记录.md)。阶段控制拆分后，事件先寄存再计数：
> 运行中读取自定义计数／溢出状态会滞后一拍；先写 0 停止再读可得到完整窗口。
> 启停、清零窗口及停止后的最终计数不变，现有 CoreMark 输出流程无需修改。
> 自由运行的 `cycle/cycleh` 没有加入这一级事件寄存。

本次已增加 RTL 统计 CSR、CoreMark 测量窗口控制及 UART 统计输出。
CoreMark 算法、种子、CRC 检查和 2000 次迭代参数保持原配置。
统计输出在 portable_fini() 中执行，发生在标准计时和结果校验之后。

## CSR 接口

| 地址 | 名称 | 含义 |
|---|---|---|
| 0x7C0 | control | bit0 使能；写 bit1 清零计数与溢出标志。写 3 清零并开始，写 0 停止 |
| 0x7C1 | window_cycles | 使能窗口内周期 |
| 0x7C2 | if_request_wait | ibus_req_valid 且 !ibus_req_ready 的周期 |
| 0x7C3 | if_input_bubbles | IF/ID 可更新且无 flush/JTAG halt，但 IF 指令无效的周期 |
| 0x7C4 | memory_stall | 执行组为 MEM，EX hold 且无 CLINT stall 的周期 |
| 0x7C5 | muldiv_stall | 执行组为 MULDIV，EX hold 且无 CLINT stall 的周期 |
| 0x7C6 | bjp_redirects | BJP 组发出跳转且无 CLINT 中断/暂停的次数 |
| 0x7C7 | bjp_instructions | BJP 组通过执行级且无执行/CLINT 暂停的次数 |
| 0x7C8 | overflow | bit0..6 分别对应 0x7C1..7C7；计数器饱和后再收到事件时置位 |
| 0x7CF | signature | 固定 0x53544101，识别接口和版本 |

计数器均为 32 位，达到 0xFFFFFFFF 后饱和而不回绕。
50 MHz 下窗口超过约 85.9 秒可能饱和；如果 overflow 非零，放弃本次占比，
缩短运行但仍满足有效 CoreMark 的至少 10 秒要求。

## 本次改动

- csr_reg.v：计数器、控制/读取接口、溢出及接口标识。
- tinyriscv_core.v：将取指、执行停顿和 BJP 事件接入 CSR。
- ifu.v：导出取指气泡事件，不改变 PC 或指令通路。
- core_portme.c/.h：在现有 start_time/stop_time 边界控制统计，结束后冻结，
  在 portable_fini 打印。增加编译器 memory barrier。
- utils.c：cycleh/cycle/cycleh 读取并在高位改变时重试，修复跨回绕读取。
- tools/bin_to_ram.py：可复用的 BIN -> 16384 行 HEX 初始化转换工具。

## 上板执行

1. 在 sw/coremark 运行 build.bat；必须看到 BUILD_OK。此次已成功编译，
   后续修改软件后仍须重新执行。
2. 生成 coremark_init.dat。本次已生成；后续可执行：

   ```bat
   python tools\bin_to_ram.py sw\coremark\coremark.bin sw\coremark\coremark_init.dat
   ```

   该命令从工程根目录运行，要求 Python 3 在 PATH。也可继续使用原操作记录
   中的 PowerShell 转换脚本。本次 BIN 19104 字节，DAT 为 16384 行。
3. PDS 打开 hardware/pds/CoreMark_PGL50H.pds，重新 Generate ram1，
   初始化文件选择本工程 sw/coremark/coremark_init.dat。
4. 从 Compile 开始完整运行 Synthesize、Device Map、Place & Route、
   Report Timing、Generate Bitstream。确认无编译错误和新增时序违例。
   统计寄存器会增加少量资源及 CSR 读取逻辑，旧时序报告不代表本版满足时序。
5. 打开 COM13（以当前电脑端口为准），115200、8N1、无流控，启用日志。
6. 用 FPGA 配置 JTAG 下载新 generate_bitstream/top.sbit，按 KEY1 重跑。
7. 等待完成，确认 Iterations=2000、CRC 通过、无不足 10 秒错误。
8. 保存从标准 CoreMark 输出到 CPU statistics v1 的完整日志。

本次未生成/下载新的 top.sbit。命令行 PDS 启动失败，尚未完成 RTL 编译、
布局布线时序或板上验证；目录中的旧 top.sbit 不能用于验证本次统计改动。
启动失败的系统错误为 WinError 623（系统 DLL 非法重定位），不是本次 RTL 编译错误。
已检查 BIN/DAT 的逐字节一致性、零填充和编译产物中的统计 CSR 指令。

## 预期输出及判读

```text
CPU statistics v1
Benchmark cycles64 : <标准计时区间的64位总周期>
Stats window cycles: <统计窗口周期>
IF request wait    : <周期> (<占比>%)
IF input bubbles   : <周期> (<占比>%)
Memory stall cycles: <周期> (<占比>%)
Mul/div stall cycles: <周期> (<占比>%)
BJP redirects      : <次数>
BJP instructions   : <次数>
Stats overflow mask: 0x00
```

若看到 `Stats CSR unavailable`，当前 RTL 返回的接口标识不匹配。
本工程旧 csr_reg 默认对未知地址返回 0，因此新版软件能给出提示；
这不是其他 RISC-V CPU 上通用的未知 CSR 探测办法。

- IF request wait 高：检查指令总线仲裁/请求路径。排除了因 EX stall
  关闭请求而导致的误计数。
- Memory stall 高：优先检查访存握手与 RAM 延迟。
- Mul/div stall 高：再区分乘法/除法或考察其实现。
- IF input bubbles 高：观察前端供给不足，可能包含总线切换和跳转后重取指。
  它不等于 RAM 等待周期，也不等于分支损失周期。
- BJP 含条件分支、JAL/JALR。redirect 是 taken 分支与无条件跳转的事件；
  尚未单独统计条件分支、未跳转分支和错误路径损失。

各事件可能重叠，不能把它们相加当作总周期。v1 首次接入时不计算 IPC/CPI，
因为现有流水线没有可靠贯穿各级的退休 valid 信号；不能用写寄存器次数
代替退休指令数。不能仅凭 redirect 数乘一个固定常数声称得到分支损失。

start_time 先清零并启用再读取 t0；stop_time 先读取 t1 再冻结。
统计窗口因此包含少量固定边界开销，比 Benchmark cycles64 略大；
软件函数调用、cycle 读取和控制访问都需要周期，差值不限定为几个周期。
UART 输出、计数器读取和百分比计算在冻结之后，不会增加硬件计数。
即使 ITERATIONS=0 自动试跑多次，每次 start_time 也会重新清零，
最终打印的是最后一次正式测量的统计。
