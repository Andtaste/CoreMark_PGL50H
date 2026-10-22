# Store快速完成版：等价简化与80 MHz时序收尾

2026-10-21。本轮明确从上轮第一版 `dual_boundary_storeack` 出发；上轮storemmio/storeprefix未混入起点。**推荐隔离候选 `dual_boundary_storewrite`：80 MHz多角setup/hold通过，IPC维持1.038308。尚未自动采纳**，当前已采纳描述仍是 `dual_boundary_slots`。

| 版本 | IPC | 估算Fmax MHz | slow setup ns | 最差hold ns | LUT | FF | 分布RAM | DRM/APM |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 当前采纳slots | 1.000230 | 80.354 | +0.055 | +0.120 | 11005 | 4475 | 709 | 48/4 |
| 上轮storeack起点 | 1.038308 | 78.691 | -0.208 | +0.097 | 10919 | 4476 | 709 | 48/4 |
| 本轮storewrite（推荐） | 1.038308 | 80.535 | +0.083 | +0.019 | 10843 | 4476 | 709 | 48/4 |
| 本轮storelogic（不取） | 1.038308 | 78.125 | -0.300 | +0.111 | 10938 | 4476 | 709 | 48/4 |

推荐版相对storeack：LUT减少76个、FF和存储/DSP数量不变，估算Fmax提升约2.343%。相对当前采纳版：LUT减少162个、FF增加1个，80 MHz同频IPC提升3.807%。固定10次窗口仍为2,704,650拍、退休2,808,261条；固定1次为271,550拍、280,944条。两份镜像CRC全部通过，性能/预测/双发/乘法/逐拍等待统计逐项相同，未增加等待拍或流水级。

## 推荐修改：移除写入的重复有效性与地址选择

原总线的MMIO写入位于 `if(da_fire)` 内部，随后才判断 `dwrite`，写地址由通用 `da` 译码。da_fire依赖dv，dv又包含EX提前load的有效性与范围判断，导致早期load地址计算进入与其无关的MMIO写控制。上轮最差路径就是操作数→AGU→MMIO译码→tohost CE，13级、setup −0.208 ns。

现有核心的发布契约已经保证：`dwrite ⇒ dv`，并且 `dwrite ⇒ da==wa`；wa始终来自MEM寄存地址。本轮把写副作用移为独立 `if(dwrite && dr)`，写目标只译码wa。MMIO读数据及错误判定仍用原da，没有把上轮整套读写译码替换方案搬进来。实际store接受条件、写数据/掩码、UART和RAM接口保持一致。这个替代依赖已有明确的核心总线契约，不是对任意独立总线输入无条件等价。

SAT对真实MEM源代码证明任意输入及状态下的写发布契约，无需复位/可达性假设；核心输出为这些信号的直接连线且本轮核心源码完全未改。随后对真实总线RTL做时序归纳，比较全部内部状态、外部响应、四个RAM使能和UART发送条件；共享任意RAM读数据和UART ready/tx，覆盖背压，不假设UART总为ready。独立真实SoC每拍再次检查该契约、已接受store不会迟发错误、分离确认归属及F/M/W未来tag。

## 额外尝试：源码更短不等于物理实现更好

storelogic在推荐改动上，将0x00000000–0x0000FFFF替为 `[31:16]==0`，将0x10000000–0x10007FFF替为 `[31:15]==17'h02000`；同时把posted_fire重用已有req_write，移除early_request中重复类型条件。两种POST_LOCAL_STORES配置的完整MEM顺序等价检查通过，实际总线归纳也通过。

另删掉未使用的request_data/request_f3临时线；它们原本就会被综合裁掉，不把删源码线数算成硬件收益。整组等价改写的物理结果反而是10938 LUT、78.125 MHz，slow setup −0.300 ns、4个失败端点；不选入推荐版。不能据此将每一项独立改写都判为无效，但本轮整体组合没有收益。推荐源码没有这些改动。

## 路径和时序边界

推荐版各角：

| 角 | slack ns | 失败端点 |
|---|---:|---:|
| Setup Summary(Slow Corner) | +0.083 | 0 |
| Hold Summary(Slow Corner) | +0.023 | 0 |
| Setup Summary(Fast Corner) | +3.568 | 0 |
| Hold Summary(Fast Corner) | +0.019 | 0 |

最差路径：`soc/cpu/operands/sm_a[0]/opit_0_A2Q1/CLK` → `soc/bus/ram_data/U_ipml_dpram_ram2_tdp/ADDR_LOOP[1].DATA_LOOP[0].U_GTP_DRM18K/iGopDrm_inv/CEB[0]`。15级，逻辑5.501 ns、布线6.657 ns，路径内最大数据扇出19。

同一路由快照只读查询：

| 目标 | setup ns | 级数 | 逻辑/布线 ns | 最大数据扇出 |
|---|---:|---:|---|---:|
| mmio_write | +4.444 | 8 | 2.417/4.836 | 16 |
| posted_completion | +4.256 | 7 | 2.635/4.971 | 217 |
| ram_controls | +0.083 | 15 | 5.501/6.657 | 19 |

MMIO写入路径已回到MEM寄存地址出发，最差余量+4.444 ns。原旁路→AGU→提前load范围判定→RAM使能仍然存在，并成为全局最差15级路径，不能宣称全部跨模块长路径已消除。原posted-store接受→MEM完成/空FIFO交接控制也仍在，定向余量+4.256 ns；EX输入信用依然只由寄存的队列占用决定，没有新增MEM ready反压到EX的组合准入链。次差取指/操作数数据路径还存在319扇出的节点，当前setup +0.154 ns。

setup最低0.083 ns、hold最低0.019 ns，均满足本次约束但余量小，尚未上板。这次只删掉不必要的控制依赖，不增加旁路级、数据复制或新执行单元。两个物理候选各跑一次PDS，真实PLL80/12.500 ns时钟、器件、约束和pnr选项与起点相同，没有false/multicycle path、改uncertainty或seed搜索。板级异步IO约束范围沿用现有工程，80 MHz结论指报告覆盖的内部时序。

## 验证、复现和保留状态

每版重新通过63项架构/ISA/随机检查、6项配对、4项取消、4项逐拍load、4项结构/lint/准入SAT、8项posted-store独立协议、6项启用快速完成的真实SoC契约和实顶层UART80完整帧检查。storelogic另跑4项MEM回退、10项地址契约、8项未来tag和4项乘法tag协议。两版都检查真实MEM发布契约和任意IP返回值下的完整总线时序归纳。推荐版除本地总线文件外，与storeack的RTL逐文件一致；操作数模块与当前采纳版SHA相同，复用其独立300000拍等价证据。

两候选均独立重建并按RTL/PLL/RAM哈希核对。归档核验历史dual_mem_ipc的1305份文件和dual_timing80的1594份文件，当前采纳描述、单发参考、固定镜像均未改变。仅清理本轮四份可再生Verilator obj缓存675,085,622字节，RTL、镜像、仿真日志、协议轨迹、STA及压缩路由快照保留。工具适配中的异步FF SAT建模和Python引号问题在独立适配脚本解决，未修改CPU以迁就检查。

固定镜像仍打印75 MHz及不接受IPC>1的软件提示，上表IPC来自独立统计窗口。短CoreMark是诊断用例，不作为正式成绩；80 MHz并非板上测量结果。

完整机器数据见 [comparison.json](dual_store_simple/comparison.json)，冻结清单见 [manifest.json](dual_store_simple/manifest.json)。
