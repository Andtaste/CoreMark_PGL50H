"""Write the integrated redesign report from frozen measurements."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def main():
 data=json.loads((ROOT/'docs/dual_legacy/comparison.json').read_text());rows=data['candidates'];fifo=rows['dual_legacy_fifo'];sel=rows['dual_legacy_select'];base=json.loads((ROOT/'simulation/results/load_bp_dual_fwd_share/performance/result.json').read_text())
 labels={'dual_legacy_fifo':'逐条FIFO＋两槽旁路/分支/乘法','dual_legacy_return':'上述组合＋完整load返回旁路','dual_legacy_split':'完整返回＋慢依赖拆对','dual_legacy_word':'仅整字load返回旁路','dual_legacy_select':'整字返回＋选择控制提前寄存'}
 lines=['# 吸收原双发结构：逐条FIFO、两槽旁路与load返回试验','',
 '2026-10-21。隔离改造及对照完成，当前采纳描述仍为dual_fwd_share。本轮五份候选均未自动采纳。','',
 '两份可通过当前75MHz约束的候选：dual_legacy_fifo偏向频率；dual_legacy_select偏向当前75MHz下的IPC。前者IPC0.911506、估计82.359MHz；后者IPC0.990019、估计75.763MHz，但慢角setup仅余0.134ns。后者相对当前采纳版同频吞吐提高约21.93%，按各自估计Fmax计算仅提高约5.23%，LUT增加约38.40%。不能只依据IPC选择。','',
 '## 对“给旁路数据加寄存器”的回答','',
 '可以截断数据组合路径，但会增加一拍传递延迟；是否仍有收益要比较结果原本何时可用。ALU结果的寄存旁路仍可早于MEM/WB写回，现有F/F1就是此类。对于本轮RAM返回直达EX的load旁路，其收益恰好是跨过WB数据寄存边界省一拍；如果再先寄存返回数据，紧邻load-use通常回到原先两拍EX空泡。要同时保留一拍load-use并寄存返回数据，需要提前请求或移动现有寄存边界。','',
 '| 逐拍位置 | FIFO组合版 | 不加数据寄存的返回旁路 | 返回旁路先加数据寄存 |','|---|---|---|---|',
 '| E0 | load EX，地址进入EX/MEM FIFO | 相同 | 相同 |',
 '| E1 | MEM接受请求，同步RAM读取 | 相同 | 相同 |',
 '| E2 | WB捕获返回数据 | 依赖消费者可同沿执行 | 返回级捕获数据 |',
 '| E3 | 依赖消费者执行 | 后续执行 | 依赖消费者执行 |','',
 '表中“旁路数据加寄存”是结构时序推导，本轮没有为了证明这个等价边界再放置重复的32位数据寄存器。select实际提前寄存的是F/F1/M/R/W/W1的tag匹配与选择控制，新增48个FF，没有给load数据新增一级。因此它保留了整字返回的一拍收益，同时仍存在RAM到旁路/EX的数据组合路径；不能把“控制寄存”称作“数据寄存”，也不能声称完全消除了长链。','',
 '## 本轮吸收了什么','',
 '- 8条逐条指令FIFO：两组奇偶bank，各4行，每个bank一写一读；RAM仍一次取回两条指令，按程序次序压入逐条队列。单发前进1条、双发前进2条，允许跨原8字节取指组配对。两个队头有寄存缓存，RAM读地址只由已寄存rd决定，take_two不进入RAM读地址。','- 两槽均支持较老结果的tag旁路与停顿期间捕获；最年轻生产者优先，WAW/同组RAW等规则保留。移除了旧滑动供给的peek/group-cross状态，保留顺序执行和成组精确退休。','- 保留联合试验中副槽条件分支、主槽条件分支搭配副槽ALU、共享流水乘法器准入，以及错误主槽分支取消副槽目的记账。','- 用同步RAM返回旁路研究缩短load-use，不恢复此前覆盖率很低且带总线ready反馈的早启动候选；EX/MEM仍249位、4深度，请求仍从该寄存边界发出。','- 慢依赖拆对单独作为组合对照：在tag编码之前把较老load/MUL/DIV依赖排除，年轻指令留在逐条FIFO供后续重配。它是保守排除任意较老慢生产者，不是完整的最年轻动态就绪判断。','- select提前准备六类结果来源的身份匹配，真实valid/data仍决定是否可用；另外将合法MUL准入的异常资格改为已寄存的指令字段，避免把通用EX地址/分支异常网络带到DSP准入。','',
 '没有增加第二LSU、副槽访存、独立退休或乱序执行；原结构中这些能力未直接复制。当前一条同步返回数据路径已经能使可通过时序的版本接近IPC1，再扩大访存结构需单独处理端口、别名、顺序与副槽异常，不能视为简单增加准入。','',
 '## 固定10次镜像对比','',
 '本表各新核版本均使用完全相同的固定10次镜像，退休2,808,261条；load548,709、store143,410、BJP571,070和五项CRC一致。均为短CoreMark诊断，不是满足正式时长条件的CoreMark认证成绩。','',
 '| 版本 | 统计窗口周期 | IPC | 相对采纳版同频吞吐 | 估计MHz | 时序 |','|---|---:|---:|---:|---:|---|',
 '| 已采纳dual_fwd_share | 3,458,702 | 0.811941 | — | 87.789 | PASS |',
 '| 上轮联合dual_joint_fix，未采纳 | 3,094,782 | 0.907418 | +11.759% | 79.942 | PASS |']
 for n,r in rows.items():
  freq=f"{r['estimated_fmax_mhz']:.3f}" if r['estimated_fmax_mhz'] else '未取得'
  lines.append(f"| {labels[n]} | {r['cycles']:,} | {r['ipc']:.6f} | {r['same_clock_gain_percent']:+.3f}% | {freq} | {r['timing_status']} |")
 lines +=['','完整返回旁路的IPC虽达到1.043685，但最差路径从RAM经子字格式化、操作数旁路进入副槽分支/结果队列，75MHz setup失败，不能采纳。只保留LW原始返回数据后缩短了路径，但word版仍有26个慢角setup失败端点。select在word基础上提前寄存匹配控制，1次、10次全部profile与word逐项完全一致，时序则通过。','',
 'split在相同完整返回基础上减少等待，却比不拆对版本慢17,921周期，不能因EX等待计数下降而称其更快。它的PDS综合/映射完成，详细布线在900秒上限内未完成，记为PDS_TIMEOUT，不提供频率、裕量或成功布线快照，不做seed重跑。','',
 '## 资源与物理时序','',
 '| 版本 | LUT | FF | 分布RAM | DRM | APM |','|---|---:|---:|---:|---:|---:|',
 '| 已采纳 | 8,339 | 4,096 | 705 | 48 | 4 |',
 '| 上轮联合fix | 10,986 | 4,324 | 775 | 48 | 4 |']
 for n,r in rows.items():
  z=r['resources'];lines.append(f"| {labels[n]} | {z['LUT']:,} | {z['FF']:,} | {z['Distributed RAM']} | {z['DRM']} | {z['APM']} |")
 lines +=['','split一行取综合/映射资源，其余候选取完成PDS后的相同资源报告。四份完成布线候选的分布RAM均709：指令FIFO64、BTB174、寄存器堆256、EX/MEM FIFO215，合计709；比上一联合方案少66，比采纳版多4。没有增加BRAM/DSP、替换RAM IP或改PLL；预先寄存匹配控制使select比word多48个FF。','',
 '| 完成PDS版本 | 慢角setup ns | 慢角hold ns | 快角setup ns | 快角hold ns |','|---|---:|---:|---:|---:|']
 keys=['Setup Summary(Slow Corner)','Hold Summary(Slow Corner)','Setup Summary(Fast Corner)','Hold Summary(Fast Corner)']
 for n,r in rows.items():
  if not r['corners']:continue
  lines.append('| '+labels[n]+' | '+' | '.join(f"{r['corners'][k]['worst_slack_ns']:.3f}" for k in keys)+' |')
 lines +=['','按各自估计Fmax折算，FIFO版相对采纳版约+5.319%，select约+5.229%；当前PLL仍约75MHz，没有实际提频或开发板验证。select在现有频率下IPC更高，但时序余量较小；FIFO版频率余量更大。不能把估计Fmax当作已验证板上运行频率。','',
 '## 关键路径与跨模块链','',
 '| 版本 | 全局最差起点 | 终点 | 级数 | 逻辑ns | 布线ns | slack ns |','|---|---|---|---:|---:|---:|---:|']
 for n,r in rows.items():
  if not r['slow_setup_paths']:continue
  p=r['slow_setup_paths'][0];lines.append(f"| {n} | `{p['start']}` | `{p['end']}` | {p['logic_levels']} | {p['logic_ns']:.3f} | {p['route_ns']:.3f} | {p['slack_ns']:.3f} |")
 lines +=['','EX/MEM输入credit仍由已寄存占用产生；没有新增MEM/总线ready到EX/ID的组合反馈。新增的是返回数据跨模块路径，及匹配控制的局部寄存边界。通过时序不等于没有长路径；select仍需关注RAM返回到消费者计算的链和局部扇出。针对队头反馈、RAM返回、操作数等待、DSP使能、重定向的完整STA保存在各候选targeted_paths。','',
 '## 正确性和证据','',
 '- 五份候选各通过63项架构/SoC/ISA检查、7项前端/RF/故障/统计检查、6项分支/乘法/滑动/精确异常配对检查、4项分支取消检查，以及固定1次、10次镜像独立退休统计和CRC。','- 每份前端有3个种子各100,000拍随机协议检查，包含双头缓存与后备bank身份、顺序PC/邻接、冲刷、过期返回和credit；每份寄存器堆累计2,400,000次读检查。','- FIFO五源队列、返回六源队列、select提前匹配队列各有300,000拍随机等价检查。word和return的操作数RTL字节相同，word共享该精确hash证据；split另跑相同队列检查。select还通过5个整核程序的未来F/F1/M/R/W身份逐拍核对。','- 全部候选通过危险lint告警排查；SAT穷举证明实际副槽准入的类型、写目的、源使用标志与完整译码一致。没有宣称整核形式证明。','- 逐拍SoC检查覆盖lw→addi、lw→store数据、lw→lw基址和后续lw→addi。FIFO版四项均两拍EX空泡，四个返回版均一拍；字节/半字在word/select中仍走WB路径，已由ISA/随机差分覆盖。','- 采纳源、单发源、PLL/IP、两份固定镜像、正式STA及前七轮不可变归档均重新核对hash。早期检查工具补充SAT后产生新版本，原工具源码按旧SHA单独归档，历史结果hash未被改写。','',
 '固定固件的串口打印仍有“retired不得大于cycles”的单发假设，因此两个IPC>1候选打印IPC/CPI unavailable；硬件计数、双退休溢出测试和独立bench计数通过，本报告直接用同一窗口退休数除周期计算IPC。没有为了改变输出而改动对照镜像。','',
 '原核心保留版的1次IPC1.020645、主槽74.26%、副槽27.81%使用不同二进制。本轮select的1次结果可在validation原始记录查看，但不据此宣称同镜像超越或精确解释原核剩余差距。没有Flash、游戏负载或开发板验证。','',
 '原始对比：`docs/dual_legacy/comparison.json`；每份候选RTL、工具、生成bench、仿真/ISA/随机/协议日志、完整STA、四份路由快照及SHA256清单均保存在`docs/dual_legacy/`。']
 at=lines.index('## 资源与物理时序')
 occupancy=['## 主副槽利用率','',
 '利用率口径为该槽退休指令数除统计窗口周期；两槽相加即IPC，不是双发指令占总指令的比例。','',
 '| 固定10次版本 | 主槽 | 副槽 |','|---|---:|---:|',
 '| 已采纳 | 75.826% | 5.368% |','| 上轮联合fix | 65.922% | 24.820% |']
 for n,r in rows.items():
  o=r['occupancy'];occupancy.append(f"| {labels[n]} | {o['primary_retire_percent']:.3f}% | {o['secondary_retire_percent']:.3f}% |")
 occupancy+=['','相对上一联合fix，单换逐条FIFO主要提高副槽持续供给；整字返回使主槽利用率从65.728%升到71.398%，副槽也升到27.603%。select的性能统计与word完全相同，额外寄存控制没有引入额外气泡。','']
 lines[at:at]=occupancy
 (ROOT/'docs/dual_legacy.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');print('WROTE docs/dual_legacy.md')
if __name__=='__main__':main()
