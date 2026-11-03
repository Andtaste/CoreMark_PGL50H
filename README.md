<h1 align="center"><strong>盘古奕芯：基于紫光同创RISC V指令集CPU设计与FPGA棋类平台</strong></h1>

当前分支：**core · 裸核性能工程**。

## 项目简介

**盘古奕芯**是一套以自研 RISC-V 顺序双发射处理器为基础的 FPGA 软硬件协同系统，将处理器微架构、SoC 集成、性能评测与双棋类智能对弈连接为完整作品。项目在紫光同创 PGL50H FPGA 上运行，既提供可复现的 CoreMark 裸核性能工程，也提供五子棋、中国象棋及 Windows 图形客户端组成的应用平台。

项目按 **CPU 设计 → SoC 设计 → 应用实现** 组织：处理器负责指令执行与搜索计算，SoC 提供存储和外设支撑，客户端完成棋盘交互、棋谱管理和运行信息展示。对弈搜索在 FPGA 板端执行，通过串口与客户端交互。

## 分支介绍

| 分支 | 定位 | 主要内容 | 适合查看 |
| --- | --- | --- | --- |
| [main](https://github.com/Andtaste/CoreMark_PGL50H/tree/main) | 完整作品主工程 | CPU、完整 SoC、DDR 接口、双棋类固件、Windows 客户端源码、构建脚本与应用位流 | 系统集成、应用演示与完整作品复现 |
| [core](https://github.com/Andtaste/CoreMark_PGL50H/tree/core) | 裸核性能工程 | CPU、跑分所需最小 SoC、CoreMark 源码与编译配置、位流和原始串口结果 | 处理器结构、裸核性能与跑分复现 |

两个分支分别保留各自完整的工程入口，可独立克隆使用。应用工程工作频率为 **91 MHz**，裸核性能工程为 **103 MHz**，成绩与对应工程配置配套记录。

## CPU 设计特点

- **顺序双发射数据通路**：围绕取指、译码与寄存器读取、操作数准备、执行、访存、写回与顺序提交组织运行；主槽与受配对规则约束的副槽协同执行。
- **缓冲与依赖管理**：取指缓冲、两项操作数队列、四项执行后 FIFO 配合八组依赖账本，管理操作数等待、年轻写者追踪、背压与冲刷恢复。
- **多路结果前递**：主副槽执行结果、乘法完成结果及双路写回参与操作数选择，缩短数据相关带来的等待。
- **分支预测与重定向**：预测查询、执行阶段校验和预测更新协同工作，并在控制流变化时恢复取指与流水状态。
- **专用运算与存储路径**：ALU、乘法流水与结果缓冲、除法单元、地址生成和 L0 数据缓存共同支撑整数运算及访存。
- **架构控制与观测**：CSR、异常与中断、返回控制、顺序提交以及性能计数器用于程序运行、控制恢复和执行效率分析。

## SoC 与双棋类应用

完整 SoC 集成处理器、本地指令与数据存储、MMIO 外设、UART 通信及 DDR 存储接口。应用镜像将五子棋、中国象棋和 CoreMark 集成在同一固件中，支持在客户端切换运行任务。

五子棋与中国象棋引擎分别负责局面表示、合法着法与候选生成、局面评估和搜索决策。中国象棋利用 DDR 存放置换表，配合板端搜索使用。客户端提供先后手选择、每步思考时间设置、停止与继续搜索、悔棋、棋谱保存与加载、复盘和辅助推荐，并显示搜索深度、节点数与耗时等运行信息。

## 成绩与复现资料

裸核 103 MHz 工程的已保存实板结果为 **514.200536 Iterations/Sec，4.992238 CoreMark/MHz**；6000 次迭代耗时 **11.668599 秒**。对应原始串口输出及分模块编译优化配置位于 `core` 分支。完整应用工程可在客户端启动 CoreMark，并记录其 91 MHz 配置下的板端结果。

## 环境与工程入口

- PGL50H-6 FBG484 / MES50HP及匹配底板，电源、Pango JTAG、USB串口。
- FPGA工具：Pango Design Suite 2025.2，入口 `hardware/pds/new_core.pds`。
- 固件重建：Python 3.10+、xPack RISC-V GCC 15.2.0，`riscv-none-elf-gcc`及配套工具加入PATH。
- `hardware/pds/source/core`为CPU；其余source目录为最小SoC、UART与顶层；`sw`为跑分固件源码。
- 位流 `output/board103/top.sbit`，原始实板输出 `output/board103/run1_uart.txt`。

克隆到英文路径，在仓库根目录执行命令。串口115200、8N1、无流控。

## 最快复现裸核跑分

1. 连接开发板电源、JTAG和USB串口；在串口工具中设置 **115200、8N1、无流控**，开启日志保存。

2. 打开 PDS Fabric Configuration，初始化 JTAG 链，选择器件，加载 `output/board103/top.sbit`，执行下载到 SRAM。

3. 程序上电运行 CoreMark；等待结束。如下载期间漏掉开头，保持串口打开后重新下载该位流。

4. 保存完整串口输出，检查 `Configured CPU Hz=103000000`、`Iterations=6000`、CRC与 `Correct operation validated`，以及最终带小数的时间/分数。

随包原实板结果 `output/board103/run1_uart.txt`：514.200536 Iterations/Sec，4.992238 CoreMark/MHz，11.668599秒。对应最终分模块优化配置详见 `reproduction/coremark_profile.json`。这份数值属于103 MHz裸核；完整SoC应记录它自己打印的实际结果。

## 从源码重建

```powershell
python tools/reproduce.py coremark
$env:PDS_HOME='D:/pango/PDS_2025.2-ads' # 改成实际安装目录
python prepare_paths.py
python tools/reproduce.py ip
```

固件按 `reproduction/coremark_profile.json` 中的最终103MHz、6000次和分模块编译策略重建，输出 `sw/build/coremark_performance_6000_reproduce`，并更新 `hardware/pds/memory`。随后打开 `hardware/pds/new_core.pds`，依次执行Compile、Synthesize、Device Map、Place & Route、Report Timing和Generate Bitstream。完整时序通过后下载新生成的 `prj_tasks/pnr_1/generate_bitstream/top.sbit`。

只需复现已发布版本时直接下载 `output/board103/top.sbit`。移动工程后重新运行 `prepare_paths.py`。修改固件后必须重新生成RAM IP和位流。

## 源码来源与复现校验

项目保留第三方软件署名、许可证和来源记录，详见 `sw` 目录中的许可证及 `PROVENANCE.json`；厂商 IP 通过对应 PDS 工具和目标器件使用。各文件适用其原有许可。

发布固件已完成重建二进制一致性校验；完整应用还完成了客户端编译、自检及双棋类主机协议测试。`SOURCE_MANIFEST.json` 提供发布文件的 SHA-256 校验值，便于核对下载内容。

## 使用提示

请使用英文工程路径，并将示例串口号替换为实际端口。一个串口同时由一个程序占用；下载到 SRAM 的镜像在断电后需重新下载。更改固件后，按本页步骤重新生成 RAM IP 与 FPGA 位流。
