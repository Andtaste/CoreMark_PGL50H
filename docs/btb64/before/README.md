# new_core

面向紫光同创 PGL50H-6 FBG484 的独立 RV32IM 单发射五级 CPU 工程。
核心、总线和外设 RTL 重新编写，没有复制旧项目 CPU，也没有 BTB、双发射或乱序执行。
复用范围为紫光生成 IP 的配置、开发板引脚约束、注明来源的 ISA 测试夹具，
以及这次移植的原项目 CoreMark 软件和打印库；CPU RTL 仍是独立实现。

当前结构为 IF → ID → EX → MEM → WB。正常 ALU 指令可连续每拍退休一条，
包括相邻 ALU 数据依赖；普通 load/store 不要求排空流水线，分支在 EX 解析。
具体协议、性能取舍和寄存边界见 [架构说明](docs/architecture.md)。
取指队首与异常地址选择优化后的源码哈希和时序见 [当前验证记录](docs/fetch_head/validation/baseline.json)，
[本轮资源、频率和功能对比](docs/fetch_head.md)。
[上轮执行控制与依赖路径记录](docs/ex_timing.md) 保留作为历史基线。
[减少等待后的记录](docs/wait_reduction/validation/baseline.json) 保留作为本轮前基线。
[逐项性能对比](docs/wait_reduction.md) 记录同一镜像的 IPC、周期和寄存边界。
[加入统计 CSR 时的记录](docs/coremark_validation/baseline.json) 和
[初始验证记录](docs/validation/baseline.json) 保留用于比较。
CoreMark 镜像、指标与运行方法见 [CoreMark 移植报告](docs/coremark.md)。

## 文件结构

```text
hardware/pds/
  new_core.pds          PDS 工程（由 new_core.tcl 生成）
  new_core.tcl          可重复执行的综合、布局布线、时序入口
  source/core/          全新 CPU RTL
  source/sys_bus/       专用 IF/LSU RAM 端口及 MMIO
  source/perips/        UART TX
  source/top/           SoC 接线
  source/source/        板级 top、PLL、复位同步
  constraints/         本开发板引脚及 50 MHz 输入时钟约束
  ipcore/              独立生成的 PLL、64 KiB/32 KiB 双口 RAM
sw/                    启动代码、链接脚本、CoreMark、打印库、演示程序及 boot.hex
simulation/            功能模型、定向/随机测试、独立指令参考模型、报告
references/isa/         47 项继承测试及来源记录
tools/                 构建、IP 生成、测试启动和验证归档工具
docs/                  微架构、接口、验证边界
```

## 构建与测试

PowerShell 在本目录运行：

```powershell
.\tools\run.ps1 -Task firmware
.\tools\run.ps1 -Task ip
.\tools\run.ps1 -Task test
.\tools\run.ps1 -Task pds
```

脚本支持 `-Python`、`-PdsHome` 参数。测试脚本支持 `--gcc`、`--iverilog`、`--vvp`。
本机使用 GCC 15.2.0、Icarus Verilog、PDS 2022.2-SP1-Lite。
复制到其他机器后先配置工具路径，再执行 firmware → ip → test → pds；
IP 生成器会把 RAM 初始化文件路径更新为新目录，无需访问旧 CPU 项目。
首次导入 IP 时的来源仅记录在 `ipcore/PROVENANCE.json`。

PDS 输入时钟 50 MHz，现有 PLL 参数产生约 75 MHz 的 CPU 时钟；UART 按 75 MHz、
115200 baud 配置。修改频率必须同步修改 PLL 和 SoC 的 CLOCK_HZ 配置。
`new_core.tcl` 不生成下载文件、不自动上板；最终硬件频率结论以当前实现的 STA 为准。

## 板上演示

当前 `boot.hex` 已选择 10 次迭代 CoreMark，复位后通过 UART 输出 CRC、耗时和性能统计。
执行 `tools/run.ps1 firmware` 可切回演示程序，再运行 `ip` 和 `pds` 更新 RAM 初始化内容。
演示程序检查内存运算，发送 `new_core RV32IM PASS`，将 GPIO 置 3、tohost 置 1。
保留原板顶层端口名与管脚。
UART RX、CPU JTAG 调试暂未实现：RX 输入未使用，JTAG TDO 固定为 0；
`halted_ind` 在本工程表示 tohost 成功，不表示调试暂停。

## 地址表

| 地址 | 功能 |
|---|---|
| 0x00000000–0x0000FFFF | 64 KiB 指令/数据 RAM，复位地址 0 |
| 0x10000000–0x10007FFF | 32 KiB 数据/可执行 RAM，栈顶 0x10008000 |
| 0x20000000 | UART TX，写低字节；忙时请求背压 |
| 0x20000004 | UART 状态，bit0=可以发送，只读 |
| 0x20001000 / 04 | 64 位 mtime 的低/高字，只读 |
| 0x20001008 / 0C | 64 位 mtimecmp 的低/高字，可写 |
| 0x20002000 | GPIO 输出，低 2 位 |
| 0x20003000 | tohost，1 表示演示成功，其他非零值表示失败 |

地址严格译码，无旧项目的大范围 RAM 镜像。未映射访问返回错误。
MMIO 寄存器使用表中对齐地址；支持字节掩码，UART 仅使用 lane0。
定时器比较值写入建议先将高字写全 1，再写低字、最终高字，避免中间值误触发。

这不是旧固件的二进制兼容替换：MMIO 地图和自定义统计 CSR 不同，软件需按新端口移植。
