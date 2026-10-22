> 本页为历史10次诊断记录。当前5000次、82MHz上板版本见[上板说明](board5000_20261022/BOARD_RUN.md)，尚无正式板上成绩。

# CoreMark 移植和测量

本页数值保留首次移植时的基线。当前单级与周转优化版本 IPC 为 0.740858、
诊断 CoreMark/MHz 为 2.638166；本轮时序收尾不改变这些指标，详见 [最新时序与配对评估](timing_pair.md)。
前一轮 [流水乘法版本](mul_pipeline.md) IPC 为 0.708081，诊断 CoreMark/MHz 为 2.521449。
已采纳的 [BTB 基线](btb64.md) IPC 为 0.667988，诊断 CoreMark/MHz 为 2.378678。
启动镜像和软件未改变，此次比较仅调整 RTL。

注意：为了固定镜像对比，UART 末尾的 `No BTB` 仍是旧固件文案，不能作为当前硬件配置依据。
当前默认 ENABLE_BP=1；0x7c6 统计实际前端纠正重定向，BTB 版本中包含方向、目标和过期预测错误。
独立仿真预测统计与关闭预测的同 RTL 对照见最新报告；以下首次移植表格仍按当时无预测口径解释。

当前 FPGA 启动镜像为 `sw/build/boot.hex`，内容与
`sw/build/coremark_performance_10/coremark.hex` 相同，已重新生成紫光 RAM IP 初始化参数。
软件镜像为 37,632 字节，HEX 补齐至 64 KiB。ELF、BIN、反汇编、链接 map 和构建参数
在相应 `sw/build/coremark_*` 目录。尚未生成下载文件或上板。

## 复用与适配范围

从原工程导入 `coremark/*.c,*.h`、`lib/xprintf.c`、`lib/utils.c` 及对应头文件，
保留原版权注释，原始文件 SHA256 记录在 `sw/PROVENANCE.json`。
CoreMark 的 list、matrix、state、util 算法文件未修改。
`core_main.c` 只增加独立 CRC 状态报告和 tohost 返回值，保留原先不少于 10 秒的规则检查。
`core_portme.c` 适配新统计 ABI；UART 驱动适配 TX 地址 0x20000000 和状态 bit0=ready。
沿用新核启动和链接脚本，并初始化 main 的 argc/argv。
旧 SPI、Flash、UART RX、调试软件没有接到不存在的硬件上。

基础机器态 CSR、异常入口以及 cycle/instret 原已实现。本次增加旁路性能计数，
无需 UART RX 即可运行、校验和输出结果。UART 为 75 MHz 配置、115200 baud、8N1。
旧 ELF/BIN 不具备新 MMIO/CSR 的二进制兼容性；这里使用移植后重新编译的镜像。

## 10 次迭代性能种子结果

GCC 15.2.0，2000 字节总工作区，RV32IM/Zicsr，原项目 O2/unroll/inline 优化选项；
新增 `-msmall-data-limit=0 -mno-relax` 以匹配新启动环境。完整 flags 随 UART 输出和 build.json 保存。
单发射，无 BTB，75 MHz 用于将周期换算为时间。
这是 RTL 短程诊断，运行约 0.081 秒，**不是正式 CoreMark 成绩或板上实测**。

| 指标 | 测量值 |
|---|---:|
| CoreMark 计时周期 | 6,068,007 |
| 统计窗口周期 | 6,068,053 |
| 退休指令 | 2,808,261 |
| IPC（UART 截断至三位小数） | 0.462 |
| CPI（UART 截断至三位小数） | 2.160 |
| 诊断 Iterations/s @ 75 MHz | 123.599066 |
| 诊断 CoreMark/MHz | 1.647987 |
| 退休 load / store | 548,709 / 143,410 |
| EX 操作数等待 | 946,490（15.597%） |
| ID 有指令但不能发射 | 2,000,579（32.969%） |
| IF 请求背压 | 0 |
| IF 输出队列空 | 944,409（15.563%） |
| MEM 事务占用周期 | 1,384,238（22.811%） |
| 乘除结果等待 | 375,840（6.193%） |
| 分支/跳转退休数 | 571,070 |
| 非顺序分支/跳转重定向 | 314,803 |
| 重定向比例 | 55.125% |
| 计数器溢出 | 无 |

性能种子 CRC 为 e9f5 / e714 / 1fd7 / 8e3a，10 次最终 CRC 为 fcaf。
验证种子的 seed/list/matrix/state CRC 为 18f2 / e3c1 / 0747 / 8d84。
两套种子都通过算法校验。原程序会对短程输出 `ERROR! Must execute for at least 10 secs`
和 `Errors detected`；在上述日志中这是运行时长不合规，独立 `CRC validation: PASS`
说明算法校验通过，不能据此将短程升级为正式成绩。

统计显示操作数依赖、访存占用和分支引起的前端空缺值得进一步研究。
ID 阻塞涵盖多种原因；EX 操作数等待也不全是 load-use。
这些计数会重叠，不能相加作为总停顿时间，不能据此推算某项优化的必然收益。
IF 请求等待为零只说明没有请求握手背压，不代表前端一直提供有效指令。
无 BTB，因此这里的重定向率不是预测错误率，也不是每次分支的惩罚周期数。
与旧核比较必须固定编译器、优化参数、迭代数、工作区和统计口径。

## 统计 CSR ABI 4

签名为 **0x4e430004**，特意与旧核区分，避免不同事件定义被误认为相同 ABI。
所有计数均为 32 位无符号，溢出置 sticky 标志；出现溢出时软件不报告比例。

| CSR | 定义 |
|---|---|
| 0x7c0 | RW：bit0 enable，bit1 clear；读回 enable |
| 0x7c1 | 窗口周期 |
| 0x7c2 | IF req_valid 且 !req_ready |
| 0x7c3 | !id_valid，包含重填和序列化期间队列空 |
| 0x7c4 | MEM 本地事务占用：!memory_ready 且 !do_trap |
| 0x7c5 | EX 有乘除且尚无结果，排除操作数未就绪及 redirect/trap 清除 |
| 0x7c6 | EX 接受的非异常、非顺序 branch/JAL/JALR 重定向事件 |
| 0x7c7 | 已退休 branch/JAL/JALR |
| 0x7c8 | RO 溢出 bitmap，bit = 计数 CSR 低四位 - 1 |
| 0x7c9 | 非异常退休指令 |
| 0x7ca | 恒 0，单发射不存在第二退休槽 |
| 0x7cb / 0x7cc | 已退休 load / store |
| 0x7cd | ID/EX 队首有指令，但操作数尚未就绪 |
| 0x7ce | id_valid 且 !issue |
| 0x7cf | RO 签名 |

采样先寄存再计数，计数值只供 CSR 读取，不控制 issue/stall/flush。
clear 丢弃前一采样；stop 会计入最后一拍已采样事件，控制 CSR 写入拍不计入窗口。
测试台用独立窗口累计和指令 opcode 分类核对周期、退休、load/store、分支计数。
计时用 cycle 的前后差；统计 enable 窗口还包含读 cycle 的边界开销，
本次相差 46 周期是预期现象。IPC/CPI 的分子和分母始终来自同一统计窗口。

## 构建与运行

从 `new_core` 目录运行；Python 路径可通过 run.ps1 的 `-Python` 指定：

```powershell
# 生成并选择启动镜像，再更新 Pango RAM 初始化和硬件实现
.\tools\run.ps1 coremark -Iterations 10
.\tools\run.ps1 ip
.\tools\run.ps1 pds

# Icarus 完整 RTL 仿真，推荐先跑 1 次
.\tools\run.ps1 coremark-test -Iterations 1

# 本机已有 WSL Ubuntu / Verilator 时，更快的同 RTL 测量
python simulation/scripts/run/coremark.py --iterations 10 --verilator --no-build
python simulation/scripts/run/coremark.py --iterations 1 --validation --verilator

# 更长的板上候选运行；仍以实际输出时长 >=10 秒且 CRC 正确为准
python tools/build_coremark.py --iterations 2000 --install
```

最后一条改变启动镜像后，也必须重新运行 `ip` 和 `pds`。
`--no-build` 精确复用已有镜像，用于模拟器交叉检查；默认重新编译。
各仿真 UART 文本、result.json、日志在 `simulation/results/coremark_*`。
仿真仅将 UART divisor 从 651 改为 8，加速计时区间外的打印；
CPU、RAM 时序和统计时钟不变。Verilator 5.032 不支持多层 defparam，
因此脚本在结果目录生成仅改变 UART 默认波特率的仿真副本，硬件源文件不变。
正常回归仍按 divisor=651 对实际 TX 波形进行解码检查。

## 实现检查

加入统计后的 PDS：5264 LUT、2929 FF、129 Distributed RAM、48 DRM、4 APM。
相对原新核基线增加 703 LUT、409 FF，RAM/DSP 数量不变。
目标时钟 75.002 MHz，slow setup +1.776 ns、slow hold +0.155 ns；
fast setup +5.119 ns、fast hold +0.110 ns，均无失败端点。
该次实现估计 Fmax 86.528 MHz，不是板上频率保证。
最差路径仍在寄存的转发 tag 到 EX/MEM 边界，统计没有新增串行全局控制链。
布局变化可能使一次实现的裕量增加，不应解释为添加计数器提升了核心性能。

14 项功能回归、47 项继承 ISA 测试通过；
统计模块启停/清零/末拍/溢出/签名单元测试通过。
完整时序、资源和源码 SHA256 见 `docs/coremark_validation/`。
原不带统计基线保留在 `docs/validation/`。
