"""Write the measured LSU comparison, limitations and cleanup ledger."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 x=read(ROOT/'docs/dual_lsu/comparison.json');a=read(ROOT/'docs/accepted_dual_baseline.json');c=x['candidates'];w=x['window_control'];cl=read(ROOT/'docs/dual_lsu/cleanup.json')
 labels={'dual_lsu_shared':'副槽访存，共用物理端口','dual_lsu_ports':'独立第二 RAM 端口','dual_lsu_forward':'第二端口＋寄存式结果旁路','dual_lsu_pair':'结果旁路＋无晚到错误保证下并行 store'}
 rows=[f"| 已采纳 dual_fwd_share | {a['coremark_stats_cycles']:,} | {a['ipc']:.6f} | {a['estimated_fmax_mhz']:.3f} | 通过 | {a['resources']['LUT']} / {a['resources']['FF']} / {a['resources']['Distributed RAM']} |",
       f"| 上轮逐条 FIFO 对照，未采纳 | {w['cycles']:,} | {w['ipc']:.6f} | {w['estimated_fmax_mhz']:.3f} | 通过 | {w['resources']['LUT']} / {w['resources']['FF']} / {w['resources']['Distributed RAM']} |"]
 for n,r in c.items():rows.append(f"| {labels[n]} | {r['cycles']:,} | {r['ipc']:.6f} | {r['estimated_fmax_mhz']:.3f} | {'通过' if r['timing_status']=='PASS' else 'setup 失败'} | {r['resources']['LUT']} / {r['resources']['FF']} / {r['resources']['Distributed RAM']} |")
 timing=[]
 for n,r in c.items():
  q=r['slow_setup_paths'][0];p=r['lsu_paths']['ram_address'][0];corner=r['corners']
  timing.append(f"- **{n}**：slow setup {corner['Setup Summary(Slow Corner)']['worst_slack_ns']:+.3f} ns，slow hold {corner['Hold Summary(Slow Corner)']['worst_slack_ns']:+.3f} ns，fast setup {corner['Setup Summary(Fast Corner)']['worst_slack_ns']:+.3f} ns，fast hold {corner['Hold Summary(Fast Corner)']['worst_slack_ns']:+.3f} ns。全局最差 `{q['start']}` → `{q['end']}`，{q['logic_levels']} 级逻辑，逻辑 {q['logic_ns']:.3f} ns、布线 {q['route_ns']:.3f} ns，数据段最大扇出 {q['max_data_fanout']}。RAM 地址端点最差余量 {p['slack_ns']:+.3f} ns。")
 text=f'''本轮完成了逐条 FIFO、滑动配对、双槽操作数旁路、扩大准入和第二本地 LSU 的组合试验。**结果未纳入基线**；正式基线仍是 `dual_fwd_share`，描述文件及其 RTL、IP、镜像和时序证据哈希均未变化。构造时使用上轮已经验证的 `dual_legacy_fifo` 作为中间对照，保留正式基线与该对照两条比较线。

时序通过的双 LSU 版 IPC 为 **{c['dual_lsu_ports']['ipc']:.6f}**，相比上轮逐条 FIFO 对照只提高 **{c['dual_lsu_ports']['vs_fifo_same_clock_percent']:.3f}%**。带寄存式返回的最高 IPC 为 **{c['dual_lsu_pair']['ipc']:.6f}**，但两版返回旁路都没有在当前 75 MHz 约束下通过 setup。扩大执行结构能提升副槽占用，但这组结果尚不足以支持继续堆第二 LSU。

**固定镜像和资源比较**

四版均运行同一份固定 10 次迭代镜像，退休 2,808,261 条指令；五项 CRC、load/store/BJP 退休计数与已采纳版一致。另有固定 1 次迭代镜像校验。所有版使用原来的 Pango PLL 与 RAM IP；实际配置仍为 75 MHz，表中 Fmax 是 PDS 估算值。短运行用于诊断，不是正式 CoreMark 成绩。

| 方案 | 统计周期 | IPC | 估算 Fmax MHz | 时序 | LUT / FF / 分布 RAM |
|---|---:|---:|---:|---|---:|
{chr(10).join(rows)}

所有方案均为 **48 DRM、4 APM**。第二 LSU 复用现有真双口 RAM 的另一端口，没有增加 BRAM 或乘法器数量。副槽在本地 RAM 上访问 A 口；IF 与该访问同 bank 时仲裁，共享端口对照则仍将两路访存串行到 B 口。随机总线测试覆盖 IF 受阻；当前 CoreMark 的副槽访存主要落在数据 RAM，测得 IF 请求等待为 0，不能推广为游戏/代码 RAM 写入也没有争用。

在同一时钟下，独立端口版相对正式基线 IPC 提升 **{c['dual_lsu_ports']['same_clock_gain_percent']:.3f}%**。若按各自估算 Fmax 乘 IPC 比较，其吞吐相对正式基线约 **{c['dual_lsu_ports']['estimated_peak_gain_percent']:+.3f}%**，相对上轮逐条 FIFO 对照也下降。当前两版时序通过的试验均能运行于原 75 MHz 约束；不能把“估算峰值下降”误解成它们在相同 75 MHz 下也更慢。

分布 RAM 从上轮 FIFO 对照的 709 增至 754。按布线网表统计，当前四版都是：逐条指令 FIFO 64、BTB 174、寄存器堆 256、EX/MEM 队列 260。增加的 45 个全部落在 EX/MEM 队列类别；其打包宽度从 249 增至 281，深度仍为 4。它们消耗可作 LUTRAM 的逻辑资源及相关布线，不会直接增加 DRM 数量。统计采用 PDS 原始资源口径。

**双发结构与顺序保证**

- 前端是 8 条逐条指令 FIFO，按奇偶分 bank，并缓存两个队头。发射一条弹一条，双发弹两条，保留滑动配对和预测信息。
- 两槽都支持已有 ALU 路径；保留副槽分支和共享流水乘法准入，新增副槽 load/store、load+load、load+store、store+load、store+store。仍是顺序、受限双发：组内 RAW/WAW 不准入，分支/乘法有相应的主槽类型限制，不是任意两条均可执行。
- 两槽共四个源操作数可等待已在流水线中的生产者，并从主副槽已有结果取值。双 LSU 不缩短 SRAM 本身的返回拍数，也不能让同一组内的 load-use 依赖同时执行。
- 第二 LSU 只接受经 EX 检查的对齐、本地、不会晚到报错的 BRAM。副槽 MMIO、越界、非对齐拆开重取到主槽，保持精确异常。主槽已经发生异常时抑制副槽架构写入，并排空已接受或已在背压中呈现的副槽读请求。
- 任一写操作涉及同一 **64 位物理行**时串行，即使是该行中两个不同 32 位字，也避免异宽 A/B 口同址读写不确定性。普通副槽 store 等主槽成功；`pair` 版只有在主请求被明确接受且总线保证不会晚到报错时，才提前并行不同物理行的 store。MMIO、未知目标、可能报错的目标保留等待。
- 两请求可独立背压、独立返回，最终仍按组退休。本轮没有独立退休、乱序访存或 EX 提前请求。

**占用率和实际收益**

四个试验在固定 10 次迭代中均有 918,448 条副槽退休，占全部退休指令的 {c['dual_lsu_pair']['occupancy']['secondary_share_of_retired_percent']:.3f}%；其中副槽 load 118,145、store 76,311。双发发射 967,776 组，占主槽发射组数的 {c['dual_lsu_pair']['occupancy']['pair_given_primary_issue_percent']:.3f}%。发射后被分支恢复冲掉的组不等同于最终退休数。

| 方案 | 主槽每拍退休率 | 副槽每拍退休率 | 同拍接受双访存次数 |
|---|---:|---:|---:|
| 上轮逐条 FIFO 对照 | {w['occupancy']['primary_retire_percent']:.3f}% | {w['occupancy']['secondary_retire_percent']:.3f}% | — |
{chr(10).join(f"| {labels[n]} | {r['occupancy']['primary_retire_percent']:.3f}% | {r['occupancy']['secondary_retire_percent']:.3f}% | {r['lsu']['same_cycle_dual_request']:,} |" for n,r in c.items())}

共享物理口版比 FIFO 对照更慢，说明只把访存放入副槽而不增加服务能力会增加成组等待。独立端口将 3,128,083 周期降到 3,068,007 周期，但相对原本 3,080,902 周期的 FIFO 对照净收益只有 0.421%。寄存主槽返回后再减少 61,351 周期；最后增加故障自由保证下的 store 并行只减少 3,500 周期，约 0.117%，并多得到 4,215 次同拍接受。

最佳仿真版仍有 EX 操作数等待 871,846 拍（29.030%）、ID 阻塞 927,201 拍（30.874%），两者有重叠，不能相加。分支错误恢复 62,047 次，占退休 BJP 10.865%。主要剩余问题包括依赖链、成组退休等待和分支恢复，第二 LSU 不能独自解决。

`shared/ports` 的 `MEM occupied` 沿用 `!memory_ready` 口径，而当时空 FIFO 也会使 ready 为低。`forward/pair` 修正 ready 的空队列语义，因而其 MEM occupied 数值明显下降，**不可把该数值差直接当作实际减少的访存阻塞拍数**。比较真实收益使用固定镜像总周期。

**长路径和寄存式旁路检查**

保留非直通 EX/MEM FIFO：`in_ready` 只取决于寄存的占用计数，不组合依赖 `out_ready`，所以 MEM 总线 ready 不会沿 FIFO 信用一路传回 EX/ID 准入。本轮也没有 RAM 原始输出经格式化后同拍进入 EX ALU。格式化后的 load 值先寄存，下一拍再供操作数网络选择。

寄存并不会使后面的选择网络自动变短：加入广播来源后，tag 比较、取值 mux、ready/执行使能、重定向等路径仍可能跨模块。本轮并未消除原有提交、异常、中断及转向控制路径。`pair` 还加入了主请求接受/无晚到错误保证到副槽请求的局部组合控制，止于 MEM/总线区域，但其布线代价仍需计算。

{chr(10).join(timing)}

`forward` 最差是 FIFO 第二条身份/操作数选择路径；`pair` 最差是乘法结果身份到 EX/MEM 写入路径。`pair` 还出现 WB valid 到 RAM A 地址端点 −0.061 ns 的路径。L0/L1 tag 到 EX/MEM 的目标查询在两版仅余 +0.138 / +0.023 ns。不能将当前失败归咎于 RAM 延迟，也不能声称加寄存器后已没有长链。

定向测试中 L0 在整组退休前有效：`forward` 的 SoC 测到 81 次、`pair` 测到 32 次，说明主槽 load 等副槽 store 时可以提前交付结果。**L1 则没有提前收益**：因为它必须等主槽成功，而此时整个组也能进入 WB，数据和 tag 与 W1 同拍相同。两版独立 8 拍任意输入有界证明均通过，同样的定向测试中提前 L1 次数均为 0。该证明不是完整核心的无界形式验证，但与 RTL 条件推导一致；本轮保留了试验原貌，未把“去掉 L1 能恢复多少频率”冒充成已测结果。后续若继续，应先只保留有实测提前收益的 L0，缩小广播网络，再考虑继续扩大 LSU。

**校验与证据**

每版通过 63 项常规架构回归、7 项前端/寄存器堆/异常/计数检查、6 项配对检查、4 项分支取消检查、3 个随机总线种子（各 30,000 拍）、3 项双访存定向检查、双访存统计与溢出检查、危险 lint 和副槽类型 SAT 证明。新增无异常访存密集程序通过三个随机延迟种子的逐条架构参考差分，覆盖 byte/halfword/word、别名和双槽 load/store。操作数网络使用三种子共 300,000 拍独立参考等价，未改网络的前两版按精确源码哈希复用已验证结果。

寄存式返回两版还通过独立 MEM 协议测试：无保证时晚到主槽错误抑制副槽 store，副槽读在较早返回时不能在主槽成功前广播，背压中的已呈现读请求在主槽错误后保持稳定并排空，数据和 tag 在响应边沿后才有效。`pair` 另测明确保证下的并行 store 和 64 位行别名阻止。

早期预检发现 UART wire 混合声明的 Icarus 语法问题，已在功能验证前修正。生成元数据中残留的旧路径/旧哈希已按精确内容保存在 `source_versions`，实际编译 override 哈希另行验证。旧异常观察器在 WB 才统计副槽抑制，而新 MEM 已提前清除其 valid；观察器改为在主槽错误完成时记录，汇编仍独立检查异常原因、EPC 和未被覆盖的副槽目标寄存器。

初次 LSU 目标时序查询用了未匹配的 ADDRA/ADDRB 名称，PDS 返回了不受该目标限制的路径。`targeted_paths/lsu_request` 因而**不能用作 LSU 结论**。最终 `lsu_paths` 使用网表真实 ADA/ADB 引脚名，并对全部返回端点/起点做匹配断言。宽范围 `lsu_feedback` 含中断计时器路径，内存寄存器路径以 `lsu_paths/memory_to_core` 为准。

完整机器可读比较在 `docs/dual_lsu/comparison.json`；四版 RTL、日志、测试轨迹、工具和路由数据库压缩快照归档到 `docs/dual_lsu`，manifest 逐文件校验。此前八份历史归档也重新校验通过。没有上板、Flash 加载或所选游戏运行结果，不能把 CoreMark 副槽访存分布推广为游戏收益。

**仿真输出清理**

已删除 {cl['removed_directories']} 个可重新生成的 Verilator `obj` 编译缓存目录，释放 **{cl['reclaimed_bytes']/1024**3:.3f} GiB**：历史缓存 186 个、约 15.821 GiB；本轮已完成固定镜像测试后的缓存 8 个、约 1.257 GiB。清理前验证目标绝对路径位于 `new_core/simulation/results` 内、目录名为 obj、没有重解析点；本轮缓存还要求对应结果为 PASS，且没有结果哈希依赖这些缓存文件。

RTL、镜像、汇编、日志、轨迹、结果 JSON、PDS 数据库和不可变历史归档保留。重跑会重新编译。逐目录清理记录在 `simulation/cleanup_result.json` 与 `simulation/cleanup_completed_lsu_result.json`，归档副本为 `docs/dual_lsu/cleanup.json`。
'''
 (ROOT/'docs/dual_lsu.md').write_text(text,encoding='utf-8')
 print('Wrote docs/dual_lsu.md')
if __name__=='__main__':main()
