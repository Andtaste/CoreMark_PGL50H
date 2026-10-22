# 整个 FPGA 目录的清理审计

> 执行状态：优先清理清单已按用户指示全部完成，删除 4,059 个文件、约 5.20 GiB，保护哈希验证通过。见[执行结果](fpga_cleanup_execution_20261022.md)。以下内容保留清理前的扫描数据。

2026-10-22。只读扫描完成，**没有删除项目文件**。共 96124 个文件、13.812 GiB（逻辑文件大小，实际回收空间可能不同；不包含随后生成的本次小型清单）。扫描未发现读取错误，没有跟随重解析目录。审计时未发现正在运行的 PDS、Icarus、Verilator 构建进程，正式清理前仍需重新检查。

| 顶层目录 | 占用 GiB | 其中优先候选 GiB |
|---|---:|---:|
| `tmp` | 7.699 | 3.643 |
| `new_core` | 5.713 | 1.491 |
| `CoreMark_PGL50H-2` | 0.293 | 0.049 |
| `CoreMark_PGL50H` | 0.103 | 0.015 |

## 优先清理：可重建缓存与可执行文件

已排除 Git 跟踪文件、27 份 manifest 所列文件、docs 证据目录及 JSON 中 SHA 输入引用。候选合计 **5.198 GiB / 4059 个文件**，类别互不重叠。这里只是清单，不代表要递归删除所有匹配目录。

| 类别 | 候选 GiB | 说明 |
|---|---:|---|
| Verilator 编译缓存：生成 C++、对象、预编译头和仿真程序 | 3.087 | 重新仿真时重新编译；保留相邻 RTL、脚本、固件和结果 |
| PDS 时序分析缓存：report_timing/rtr.db | 1.352 | 保留输入 top_pnr.adf 与文本 top.rtr；重新分析时生成数据库 |
| Icarus 编译后的仿真可执行文件：*.vvp | 0.620 | 保留 testbench 和日志，需要运行时重新调用 iverilog |
| PDS compile/ 解析及编译中间文件 | 0.139 | 保留工程、RTL、约束、IP 和最终检查点；重新编译时生成 |
| Python __pycache__/ 与 *.pyc | 0.001 | Python 自动再生成，体积很小 |

大部分 Verilator 缓存位于 tmp，已识别 30 个构建目录。示例（MiB）：

- `tmp\native_current_limits_probe\obj`：179.4 MiB。
- `tmp\new_core_baseline_import_20261021_151158\previous_worktree\simulation\firmware\generated\native_ooo\native_obj`：178.4 MiB。
- `tmp\native_ooo_obj`：172.9 MiB。
- `tmp\ooo2_integrated_20261019\obj`：165.8 MiB。
- `tmp\ooo2_cut_control_20261019\obj`：165.8 MiB。
- `tmp\ooo_btb32_20261017\obj`：164.5 MiB。
- `tmp\native_age_unit_obj`：164.3 MiB。
- `tmp\ooo_alu_age_20261017\obj`：164.3 MiB。

PDS 时序数据库分布：new_core 158 个约 0.971 GiB，tmp 56 个约 0.371 GiB，旧 CoreMark_PGL50H-2 两个约 0.010 GiB。应清理的是数据库文件，不是整个 report_timing 目录；其中的文字报告应保留。

## 可以进一步整理，但不能直接删除

- **综合/布局布线检查点候选约 4.019 GiB**：*.adf、*_syn.vm、*.netlist、snr.db、*.snr。先排除当前采纳版和原生产单发对照，再确认已有压缩归档并校验可恢复，才能删除历史原副本。删除后不能直接做增量布局、定向 STA 或综合网表分析，需恢复或重跑。这个数量只是待审范围，不是额外保证可回收空间。
- **未纳入冻结保护的日志和 trace 约 0.372 GiB**：历史回归可压缩整理。最新功能证明、失败诊断、计数来源应保留；尚未逐项判断每份日志的用途。
- 其余数据库约 0.073 GiB，需逐类确认用途。
- `tmp/nax_tools` 约 0.660 GiB，是 JDK/SBT/Scala 等研究依赖；参考 CPU 仓库和源码快照也不是普通缓存。只有确认不再做对应研究，才适合整体冷归档。

## 默认保留

- **不能整删 new_core/simulation/results**：当前采纳核心的 RTL 位于 `load_bp_dual_boundary_storewrite`，后续生成器和验证工具还引用历史候选。
- **不能整删 tmp**：`tmp/iverilog-portable` 是现有测试工具依赖；accepted/source/backup 快照可能是旧项目或生成器的输入。
- `.git`、项目 RTL 源码、PDS 工程入口和约束、紫光 IP 配置/封装/初始化文件。
- `sw` 和 `sw/build` 中的 CoreMark/boot/FLASH 镜像、链接脚本、初始化 HEX、ELF/BIN 等固件证据；不能因为它们来自构建就整目录清空。
- `new_core/docs` 约 1.549 GiB：包含冻结的源码、STA、回归和路由快照，不混入这次缓存清理。
- `accepted_baseline.json`、`accepted_dual_baseline.json`、result.json、manifest.json、关键 top.rtr、归档 ZIP，以及被证据哈希引用的原始文件。

推荐先清理上述 **5.20 GiB** 的逐文件候选，再决定是否整理历史检查点。正式执行前复核每条路径、大小、修改时间、引用保护和在运行任务；清理目录时不能连带删除目录内的保留项。

原始数据：[目录与分类统计](fpga_cleanup_audit_20261022/inventory.json)、[逐文件候选清单](fpga_cleanup_audit_20261022/candidate_files.json)、[数据库明细](fpga_cleanup_audit_20261022/database_details.json)、[保护引用](fpga_cleanup_audit_20261022/protected_references.json)。
