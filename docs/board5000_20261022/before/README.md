# new_core

当前主 PDS 工程为 [hardware/pds/new_core.pds](hardware/pds/new_core.pds)，已同步采纳的 **pairbranch 双发基线**，PLL **82 MHz**。工程源码、IP 和 CoreMark 初始化镜像均位于 `hardware/pds` 内。构建入口为 `hardware/pds/new_core.tcl`，见 [82MHz多seed验证](docs/clock82_multiseed_20261022/README.md)、[此前目录同步记录](docs/pds_main_sync_20261022/README.md) 和 [主工程基线绑定](docs/active_pds_baseline.json)。旧工程完整保存在 `hardware/pds_before_pairbranch_20261022`。

[资源优化试验](docs/dual_resource_trials.md) 完成：上一轮推荐的 `dual_boundary_next_pairbranch` 已采纳。副槽 PC 重建、EX/MEM 队列 PC 压缩、合并压缩、比较逻辑共享四版均保持 IPC 不变，但均未通过 80 MHz，本轮四个资源候选已按用户指令明确不采纳；当前基线继续为 pairbranch，见 [决定记录](docs/dual_resource_trials_decision.json)。详见 [采纳记录](docs/dual_pairbranch_adoption/adoption.json)。

[旁路到控制端的路径与扇出试验](docs/dual_forward_control.md) 完成：队首选择展开、下一PC选择重排、局部指针复制三版均保持IPC不变，但均未通过80MHz，不建议合入。指针最大直接扇出829→402也未带来整核收益；当前采纳基线保持不变。

[等价简化、时序与冗余审计](docs/dual_timing_simplify.md) 完成：三种保持 IPC 不变的改写均未通过 80 MHz，不建议合入；局部 RAM 使能改善后，瓶颈转移到其他控制路径。当前采纳基线保持不变。

[乘法末级交接与双发统计试验](docs/dual_mul_tail.md) 完成：两候选IPC1.041188（+0.277%），但均未满足80 MHz，不建议采纳。该轮以历史基线 `dual_boundary_storewrite` 为对照；报告包含按副槽类型细分的RAW、资源冲突和准入机会。

当前已采纳的双发开发基线为 **`dual_boundary_next_pairbranch_clock82`**：原 pairbranch CPU 结构不变，真实 PLL **82 MHz**，布局 seed **22**／路由 seed **4**，多角 setup/hold 通过，估算 Fmax **82.271 MHz**、IPC **1.040582**。布线后资源 **11029 LUT / 4476 FF / 709 分布 RAM / 48 DRM / 4 APM**，映射阶段为11013 LUT。主工程位于 `hardware/pds`，见 [当前采纳记录](docs/accepted_dual_baseline.json) 与 [82MHz多seed报告](docs/clock82_multiseed_20261022/README.md)。完整复现入口 `new_core.tcl` 会检查源码和完整结构连线，再使用[固定映射检查点](hardware/pds/checkpoints/README.md)；修改输入后须重新综合和收敛。此前 80 MHz 工程完整保存在 `hardware/pds80_before_clock82_20261022`，尚未上板。

此前store快速完成试验见 [MEM等待与IPC试验](docs/dual_mem_ipc.md)；其中三版当时均未达到80 MHz，本次仅采纳后续MMIO写控制简化版。上一采纳版本 `dual_boundary_slots` 及迁移后的 `hardware/pds_before_pairbranch_20261022` 单发工程保留对照。

以下早期单发设计说明为历史资料；当前双发工程以文首主入口和基线记录为准。

面向紫光同创 PGL50H-6 FBG484 的独立 RV32IM 单发射五级 CPU 工程。
核心、总线和外设 RTL 重新编写，没有复制旧项目 CPU。当前加入 64 项带 tag 的 BTB，
每项用 1 位已解析局部历史选择两组 2 位方向计数器，保持单发射、顺序执行。
复用范围为紫光生成 IP 的配置、开发板引脚约束、注明来源的 ISA 测试夹具，
以及这次移植的原项目 CoreMark 软件和打印库；CPU RTL 仍是独立实现。

当前结构为 IF → ID → EX → MEM → WB。正常 ALU 指令可连续每拍退休一条，
包括相邻 ALU 数据依赖；普通 load/store 不要求排空流水线，分支在 EX 解析。
具体协议、性能取舍和寄存边界见 [架构说明](docs/architecture.md)。
BTB64 与八项取指 FIFO 已采纳，见 [BTB 基线记录](docs/btb64.md) 和
[采纳状态及源码哈希](docs/accepted_baseline.json)。
局部历史预测和 MEM 响应后的非访存暂存版已采纳，见 [IPC 优化记录](docs/ipc_opt.md)。
当前已采纳版进一步简化 EX/MEM 辅助字段生成，估计 Fmax 89.638 MHz，见 [EX/ID 单级路径实验](docs/ex_id_finish.md) 和
[当前验证记录](docs/ex_id_finish/validation/baseline.json)。生产核心仍为单发；
[受限双发整核实验](docs/dual_issue.md) 已实现隔离候选，同频提升 4.230%，但频率和资源成本使本轮暂不建议采纳。
[双发 RAM 与冗余优化](docs/dual_ram.md) 将分布式 RAM 859 → 705、DRM 96 → 48，IPC 不变；完成等价检查及紫光 IP 初始化读回，保留隔离候选，正式版本未替换。
[MEM→IF 控制路径实验](docs/dual_bus.md) 将目标路径压至 4 级，但整核仍受 IF 分类路径限制且 Fmax 下降；两候选不建议采纳，保留上轮双发研究起点。
[IF 最长路径调整](docs/dual_if.md) 部分判定在原 IF 边界寄存，双发估算 Fmax 83.382 → 84.710 MHz，IPC 与 RAM 数量不变；用户已确认保留研究候选，正式单发未替换。
[FIFO 高扇出实验](docs/dual_fan.md) 通过引导复制/四组指针将已测局部负载降至 64 以内，但整核频率下降；不合入，继续保留 84.710 MHz 候选。
之前的配对结构评估保留在 [时序与双发配对报告](docs/timing_pair.md)。
[Load 启动与分支预测研究](docs/load_bp_research.md) 保存独立副本实验；这些候选没有替换已采纳核心。
[Load-use 逐拍结构验证](docs/load_cycle_structure.md) 记录提前备址的条件性省拍结果、覆盖机会和接入限制，尚未接入主核心。
[提前 load 整核接入实验](docs/early_load_integration.md) 已验证局部少一拍；同频提升 0.389%，但频率和控制链代价不合适，用户已明确拒绝两个候选。
[分支预测筛选与整核实验](docs/bp_study.md) 比较 27 个模型，验证折叠 BTB/RAS；最高同频收益 1.523%，但频率和资源成本不合适，用户已明确拒绝本轮候选。
[单级逻辑与访存周转记录](docs/stage_opt.md) 保留为本轮前基线。
[流水乘法记录](docs/mul_pipeline.md) 保留为本轮前基线。
[单级路径、等待拆分与 RAM 映射检查](docs/stage_opportunities.md) 记录后续优化依据。
[取指队首与异常地址选择记录](docs/fetch_head.md) 保留为无预测基线。
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

- [操作数转发选择与逻辑复用实验：87.789 MHz，减少 185 LUT](docs/dual_fwd.md)

历史采纳版本 `dual_fwd_share`（已被后续版本替代）：87.789 MHz、8339 LUT、4096 FF、705 分布式 RAM、48 DRM、4 APM；IPC 0.811941。源码与验证入口见 [双发采纳记录](docs/accepted_dual_baseline.json)。上文各轮研究结论为历史记录；`hardware/pds` 下原单发工程保留对照，当前双发源码位于 `simulation/results/load_bp_dual_fwd_share`。

- [双发准入与跨组窗口：IPC 最高 0.831262，但本轮不合入，保留 87.789 MHz 基线](docs/dual_admit.md)

2026-10-21 历史采纳：`dual_boundary_launch`，IPC 1.000230、PDS Fmax 77.760 MHz、11498 LUT / 4495 FF / 709 分布RAM / 48 DRM / 4 APM。当前双发源位于 `simulation/results/load_bp_dual_boundary_launch`；见 [当前采纳记录](docs/accepted_dual_baseline.json) 与 [本次采纳记录](docs/dual_boundary_adoption/adoption.json)。此前各轮记录为历史结论。下一轮目标为80 MHz，原75 MHz PLL和单发工程保留。

80 MHz时序试验完成：推荐 `dual_boundary_slots`，详见 [统一报告](docs/dual_timing80.md)。`dual_boundary_slots` 为历史采纳版本；现由 `dual_boundary_storewrite` 作为后续优化基线。
