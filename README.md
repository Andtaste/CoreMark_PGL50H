# 当前主工程：83 MHz，比较指令正确性修复（2026-10-23）

入口仍为 **[hardware/pds/new_core.pds](hardware/pds/new_core.pds)**，或双击 `open_main.cmd`。新下载文件为 **[output/board83/top.sbit](output/board83/top.sbit)**，与主工程 `download/top.sbit` 相同。83MHz、5000次、o3_inline80固件未变；布局/布线种子为9/1，fanout64。请重新下载新文件。

已修复ADS综合后部分无符号ALU/分支比较在最高位不同时误用有符号结果的问题：显式区分最高位的符号语义。旧网表能重现板测的360.567664和IPC unavailable；新网表使用原固件报告机器码及同一计数器值重放，输出 **Iterations/Sec 360.941214、IPC 1.105、CPI 0.904**。CoreMark/MHz仍为4.348689。软件统计公式、编译选项没有修改。

63项当前整核/SoC/ISA回归和RTL执行单元等价检查通过；原RTL完整5000次仿真的CRC及计数器与用户板测相符。新网表报告重放通过，83MHz布局布线四角STA通过：Fmax 83.368MHz，最差setup +0.053ns。网表重放加速了UART/PLL且使用零延迟厂商模型，不能代替新bitstream的实板验证；用户已用新文件完成实板复测：5000次CRC PASS，360.941214 CoreMark、4.348689 CM/MHz、IPC 1.105、CPI 0.904，计数边界PASS；与修复后预期一致。

旧主工程完整保留于 `hardware/pds_before_compare_fix_20261023`，其旧下载文件存在已复现的比较错误，仅作历史对照。诊断证据见 [diagnosis.json](simulation/results/report_large_20261023/diagnosis.json)，时序和下载哈希见 [release_result.json](hardware/pds/release_result.json)。测试缓存、逐指令轨迹已清理，保留脚本、日志和结果。以下均为修复前历史记录，其入口、哈希和通过结论不代表当前版本。

# 当前本机主工程：83 MHz（2026-10-23）

已将采纳配置同步到 **[hardware/pds/new_core.pds](hardware/pds/new_core.pds)**。可直接打开工程，或双击根目录 `open_main.cmd`。83MHz PLL、布局/布线种子7/2、fanout64、四角优化、hold修复、引脚和5000次 `o3_inline80` 固件均已写入，无需手工调整。

本机下载文件：**[output/board83/top.sbit](output/board83/top.sbit)**；主工程内也有 `hardware/pds/download/top.sbit`。连接FPGA配置JTAG后在PDS中执行SRAM下载，串口115200/8N1/无流控，按KEY1启动。串口号、下载器按实际设备选择。详细说明见 [hardware/pds/README.txt](hardware/pds/README.txt)。本次按最终要求只交付本机主工程和下载文件，没有额外便携包。

主目录完整综合、布局布线、四角STA和bitstream生成通过；Fmax83.091MHz，最差setup裕量+0.013ns。RAM36576项检查、UART720周期检查通过。尚未实际下载或取得板测结果。默认 `tools/run.ps1 -Task pds` 现在构建主工程、检查时序并更新 `output/board83/top.sbit`。主工程输入清单为 `hardware/pds/main_manifest.json`，下载文件哈希及STA为 `hardware/pds/release_result.json`。

旧主工程完整备份于 `hardware/pds_before_main83_20261023`；旧82MHz采纳工程和旧 `output/board5000/top.sbit` 均保留。下面是此前优化记录，出现的“当前默认工程”以本节主工程入口为准。

# 83MHz采纳记录（2026-10-23，多种子验证后）

当前默认工程为 [hardware/pds_optimized_inline80_clock83_20261023/new_core.pds](hardware/pds_optimized_inline80_clock83_20261023/new_core.pds)：原采纳RTL、`o3_inline80` 固件、实际83MHz PLL、`fanout_guide=64`、布局/布线种子7/2。六组完整实现中一组通过，另一次独立完整重建复现相同四角时序与资源结果，Fmax83.091MHz。最差建立裕量仅 **+0.013ns**；保持裕量慢角+0.168ns、快角+0.116ns。该结果是工具验证通过，尚未上板测量。

相同10次当前固件仍为2299628周期，CRC与独立计数器通过，厂商RAM36576项检查及UART720周期检查通过。82→83MHz按相同周期数推算吞吐提高 **1.2195%**，CM/MHz不变。资源LUT11046→11387、FF4437→4547，分布RAM709、DRM48、APM4不变。按吞吐优先原则采纳；5000次ROM已生成并完成物理实现，未运行完整5000次仿真、未上板、未生成新下载文件。

默认入口 `tools/run.ps1 -Task pds` 和 `-Task coremark` 读取 [active_compiler_profile.json](docs/active_compiler_profile.json)。直接构建固件可用 `python tools/build_coremark.py --profile o3_inline80 --source-date-epoch 1792684800 --iterations 5000 --cpu-hz 83000000 --tag inline80_clock83`。原82MHz完整工程保留于 `hardware/pds_optimized_inline80_20261023`，原组合配置保留于 [compiler_profile_clock82_preserved.json](docs/compiler_profile_clock82_preserved.json)。六组对照见 [sweep_results.json](simulation/results/continuous_clock83_inline80_sweep_20261022/sweep_results.json)。下面各节为历史记录。

# 前一版82MHz组合基线（2026-10-23，保留）

已采纳 **原82MHz RTL＋O3、内联阈值80的软件配置**。当前完整工程为 [hardware/pds_optimized_inline80_20261023/new_core.pds](hardware/pds_optimized_inline80_20261023/new_core.pds)，配置与证据见 [active_compiler_profile.json](docs/active_compiler_profile.json)。两次独立完整实现均通过82MHz全角时序，Fmax83.043MHz，LUT11046、FF4437、分布RAM709、DRM48、APM4，与原RTL基线相同；固件从39168增至54260字节，仍在64KiB容量内。

同源、同构建时间、同82MHz元数据的100次诊断对照：原选项26010275周期，新配置22995853周期，吞吐提升 **13.1085%**，CM/MHz **3.844634 → 4.348610**。固定1验证、10/100次CRC和独立计数器、10次独立重建重复、36576项厂商RAM检查、实际顶层UART检查通过。硬件ROM为5000次固件，但未执行完整5000次仿真或上板测量，以上不是正式板测CoreMark成绩。

本轮83MHz扇出优化与27单元局部布局试验均未通过最终时序，不采纳；主频保持82MHz。

`tools/run.ps1 -Task pds` 现在重建此组合工程并核验时序。`tools/run.ps1 -Task coremark` 默认使用已采纳配置，独立命名输出，保留历史固定镜像；指定 `-CompilerProfile baseline` 可构建原编译选项。也可直接使用 `python tools/build_coremark.py --profile o3_inline80 --source-date-epoch 1792684800 --iterations 5000 --cpu-hz 82000000 --tag inline80`。未生成新下载文件，原 `output/board5000/top.sbit` 未变。

[active_optimization_baseline.json](docs/active_optimization_baseline.json) 继续记录原固定镜像下的RTL基线及其2.72%历史收益；软件配置绑定其哈希，RTL基线改变后会拒绝沿用未经重新验证的配置。不要把历史镜像与重编译镜像之间的差异全算作编译优化收益。下文“当前”均为保留的历史记录。

# 当前自主优化基线（2026-10-22）

已采纳 **缩短乘法流水线＋乘法配对准入改进＋64项BTB索引折叠优化**：工程 [hardware/pds_optimized_mul_early_products_20261022/new_core.pds](hardware/pds_optimized_mul_early_products_20261022/new_core.pds)，实际PLL **82 MHz**。乘法接收时直接寄存部分积，低/高半结果均提前一拍，保留令牌结果缓冲和广播冲突规则。相同fixed10诊断固件周期 **2665285 → 2627125**，较上一基线吞吐提升 **1.453%**，CM/MHz **3.751944 → 3.806442**；较原上板基线累计吞吐提升约 **2.72%**。两次独立完整物理实现的四角时序和资源结果一致，估算Fmax **83.043 MHz**；LUT **11016 → 11046**、FF **4476 → 4437**，分布RAM709、DRM48、APM4不变。完整回归、固定1/10 CRC、9万周期独立乘法模型及配对/前递/访存/预测取消检查通过。估算Fmax不代表实际提频或板测结果，短诊断不作为正式CoreMark成绩。

后续优化以 [active_optimization_baseline.json](docs/active_optimization_baseline.json) 为准。`tools/run.ps1 -Task pds` 从该基线完整重建并核验STA；它不生成下载文件。此前两轮基线完整保留在 `hardware/pds_optimized_mul_fold10_20261022` 和 `hardware/pds_optimized_20261022`；原上板工程和 `output/board5000/top.sbit` 保留原版，未被新RTL替换。原始完整备份在 `simulation/results/autonomous_20261022/original_board`。候选的采纳/拒绝原因、测试与续跑说明见 [持续优化记录](simulation/results/autonomous_20261022/PROGRESS.md)。下方其余“当前”描述均为历史版本记录，以本文首入口为准。

# 原CoreMark5000上板版本（保留）

当前上板入口：`hardware/pds_board5000/new_core.pds`；下载文件：`output/board5000/top.sbit`。PLL与软件计时均为82 MHz，5000次迭代。配置/镜像/短验证已检查，新镜像四角时序通过，完整5000次仿真按用户要求停止，等待上板实测。见[上板说明](docs/board5000_20261022/BOARD_RUN.md)。完整重建使用`python tools/build_board5000.py`。

原固定10次采纳工程`hardware/pds`及其82MHz证据保留，用于历史对比。

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

## 5000次上板工程PDS重新验证

此前冻结布局下载文件因板级引脚约束未生效已撤回。当前`hardware/pds_board5000/new_core.pds`已从源文件完整重跑两次，实际引脚与FDC一致；布局3 / 路由1，估算Fmax82.055MHz，慢角setup+0.008ns；布线后11037LUT /4476FF /709分布RAM /48DRM /4APM。详情见`docs/board5000_20261022/PDS_VERIFICATION.md`，请使用新生成的`output/board5000/top.sbit`。原`hardware/pds`历史10次诊断工程原样保留，但原22/4报告同样没有应用正确板级管脚约束，不能作为可上板收敛依据。
