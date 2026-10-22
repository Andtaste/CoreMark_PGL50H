"""Write the human-readable report from frozen comparison measurements."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))

def main():
 c=read(ROOT/'docs/dual_types/comparison.json');v=c['candidates']
 base=read(ROOT/'simulation/results/load_bp_dual_fwd_share/performance/result.json')
 bp=c['baseline_pds'];bc=int(base['metrics']['Stats window cycles']);bi=int(base['metrics']['Retired instructions'])/bc
 lines=['# 副槽类型、共享乘法器与滑动跨组配对研究', '', '2026-10-21。研究完成，未采纳；正式采用的双发基线仍为 `dual_fwd_share`。本轮所有 RTL、仿真、布局布线均隔离在 research results 中。', '',
 '## 结论', '',
 '用户提出的“未双发前进4字节、双发前进8字节”可以用于发射窗口头指针。隔离候选已经实现 `[A,B]` 单发后变成 `[B,C]`、双发后变成 `[C,D]`、阻塞消耗0条；取指请求仍按原64位带宽独立预取，预测跳转与异常重定向单独处理。', '',
 '最终滑动候选同频吞吐提高3.009%，但估计Fmax从87.789降到83.598 MHz；各自按估计Fmax运行，吞吐反而下降1.909%。该组合需要至少85.225 MHz才能追平原基线。因此保留原基线，研究候选供后续拆解优化，未覆盖已采纳代码。', '',
 '## 583,920次副槽类型不允许的拆分', '',
 '以下是字节完全相同的基线RTL和镜像，在仿真bench中增加计数器得到的基准统计。每次计数属于一种指令类型；依赖、资源、预测等拒绝原因可以重叠，不能把各列相加当成互斥原因。', '',
 '| 副槽类型 | 次数 | 同组RAW | 同组WAW | 依赖更老指令 | 资源冲突 | 普通ALU主槽且依赖/资源等检查通过的机会 |',
 '|---|---:|---:|---:|---:|---:|---:|']
 labels=['条件分支','JAL','JALR','MUL/MULH/MULHSU/MULHU','DIV','Load','Store','CSR','其他']
 for label,p in zip(labels,c['type_profile']):lines.append('| '+label+' | '+' | '.join(f"{p[k]:,}" for k in ['count','raw','waw','older_dep','resource','clean_plain'])+' |')
 lines += ['', '分支与跳转合计315,047次，乘法36,720次、load 144,746次、store 87,406次，另有1次CSR。最后一列只是本轮约束下的准入机会，不代表能节约相同周期数；条件分支允许携带第二条预测结果，跳转尚未实现副槽准入。原准入门的预测拒绝次数分别为条件分支240,508、JAL 19,256、JALR 19,155，和其他拒绝原因重叠。', '',
 'Load的98,890次、store的67,394次资源冲突指同组主槽也使用LSU；并不等同于总线当拍busy。乘法在本轮“主槽普通ALU”约束下不竞争同组乘法器，仍会受提交、结果等待和更老依赖影响。', '',
 '## 前端没有第二条与跨组机会', '',
 '| 来源 | 次数 | 含义 |', '|---|---:|---|',
 '| 组内上一拍单发后的剩余指令 | 1,070,546 | 原结构将剩余上半条单独发出，未与下一组低半条组合 |',
 '| 取指入口本来就在上半字 | 204,335 | 例如跳转目标地址为8字节组的高半字 |',
 '| 预测taken截断本组 | 122,754 | 顺序下一条不能直接使用，须保留预测路径语义 |',
 '| 合计 | 1,397,635 | 统计发生在主槽已经发射而第二条未提供时；不能理解成前端全空 |', '',
 '组内剩余占上述单条供给的76.6%。基线中下一组已缓冲、地址连续、普通ALU副槽且依赖/资源检查通过的跨组机会有108,773次。实现后会改变后续分组和等待节奏，实际跨组发射数不能和这个离线机会数直接相减。', '',
 '## 实现边界和冗余检查', '',
 '- 副槽扩展限于条件分支与四种乘法；扩展配对的主槽必须为合法普通ALU、无主槽BTB命中。保留既有ALU副槽配对规则；同组RAW/WAW拒绝，WAR允许。没有副槽JAL/JALR、LSU或除法器。',
 '- 条件分支携带原预测结果，在执行级比较实际下一PC。副槽分支没有寄存器写回，使用已有副槽结果空间携带分支下一PC；精确异常与有序提交保持组内顺序。',
 '- 共享原有流水乘法器，结果标签增加槽位标志，APM维持4个。副槽执行器显式关闭除法器，防止可变kind意外综合出第二个除法器。',
 '- 滑动版保留4组、最多8条的原存储结构，只缓存下一组低半条及其预测/预译码信息。邻接信息在取指命令、在途和缓存之间寄存，不在ID新增32位PC比较。跨组成功后可消费1或2个组；消费两个单条组后缓存有一次重新填充机会，故不保证每拍都能跨组配对。',
 '- 原操作数tag队列完全不改，EX/MEM保持249位、4深度，MEM ready仍在寄存credit边界终止。没有增加四操作数等待网络，也没有把后端ready组合贯穿到取指命令生成。',
 '- 实测发现并移除了“主槽预测比较结果→副槽乘法接收”的冗余门控；配对类型和写目的检查改用已寄存预译码标志。WB分支、MEM副槽乘法识别采用已准入指令集合内的简化比较。实际分类函数对完整32位指令空间做局部SAT证明，验证这些简化与全译码一致；这不是整核时序等价证明。', '',
 '## 同一镜像的性能和物理结果', '',
 '固定10次镜像，所有版本退休2,808,261条，load/store/BJP退休数及CRC一致。IPC使用完整计数重新计算，周期为Stats window cycles；短CoreMark仅作诊断。Fmax为同一约束/选项的一次路由估算，PLL实际仍约75MHz。', '',
 '| 候选 | 周期 | IPC | 同频吞吐变化 | Fmax MHz | LUT | FF | 分布RAM | 各自Fmax吞吐变化 | 时序 |',
 '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|',
 f'| 已采纳基线 | {bc:,} | {bi:.6f} | — | {bp["estimated_fmax_mhz"]:.3f} | 8,339 | 4,096 | 705 | — | PASS |']
 names={'branch':'仅副槽条件分支','mul':'仅共享乘法准入','both':'两项组合初版','compact':'组合简化译码','slide':'组合加滑动初版','bound':'组合移除冗余DSP门控','slide_bound':'滑动移除冗余DSP门控','admit':'组合改用寄存准入','slide_admit':'最终滑动＋寄存准入'}
 for suffix,label in names.items():
  x=v['dual_types_'+suffix];r=x['resources']
  lines.append(f'| {label} | {x["cycles"]:,} | {x["ipc"]:.6f} | {x["same_clock_gain_percent"]:+.3f}% | {x["estimated_fmax_mhz"]:.3f} | {r["LUT"]:,} | {r["FF"]:,} | {r["Distributed RAM"]} | {x["estimated_peak_gain_percent"]:+.3f}% | {x["timing_status"]} |')
 lines += ['', '所有版本DRM=48、APM=4。组合初版有slow hold −0.100ns、fast hold −0.068ns，不能作为通过时序的候选；提高频率不能消除hold违例。各变体的Fmax波动包含布局布线差异，不应从单次结果断言某个局部逻辑改写必然更快。最终滑动版四角均无失败端点：slow setup1.371/hold0.164ns，fast setup4.898/hold0.116ns。', '',
 '副槽退休计数来自额外bench census，重复同一RTL/镜像，完整性能、双发、乘法和预测计数与原测量逐项一致；对语义相同的compact/bound/admit版本，另验证两张镜像下完整profile相同后引用census。', '',
 '| 副槽退休组成 | 基线 | 仅分支 | 仅乘法 | 两项组合 | 最终滑动组合 |',
 '|---|---:|---:|---:|---:|---:|',
 '| 普通ALU | 185,671 | 185,671 | 172,711 | 172,711 | 255,918 |',
 '| 条件分支 | 0 | 16,969 | 0 | 16,969 | 17,516 |',
 '| 乘法 | 0 | 0 | 16,560 | 16,560 | 50,400 |',
 '| 总数 | 185,671 | 202,640 | 189,271 | 206,240 | 323,834 |', '',
 '仅分支发射22,506次但退休16,969次，其差包含被冲刷的错误路径；恰好节约16,969周期。仅乘法新增16,560条副槽乘法，却减少12,960条普通ALU副槽退休，乘法队首等待从37,880升到44,360、操作数等待和MEM占用各增加6,480，净周期反而增加2,880。说明共享单元准入有收益机会，也会改变结果可用时间、组提交与后续保守依赖阻塞，不能只看新增配对数。', '',
 '最终滑动版发射342,778个双发组/2,546,421个总发射组，发射配对率13.461%；副槽退休占全部退休11.531%（基线6.612%）。实际跨组发射148,618次，其中同时弹出两组502次。乘法连续接收峰值从1升到2；预测解决数/错误数不变，恢复期间IF空拍由123,986变为124,283。', '',
 '## 长路径实测', '',
 '保留寄存边界并不意味着模块间控制路径已经消失。本轮不能声称“没有长链”；滑动选择、依赖准入和头部更新构成的反馈仍需重点处理。以下来自相同已路由ADF的定向STA，未重新实现。', '',
 '| 最终滑动版路径范围 | 起点 | 终点 | 逻辑级数 | 逻辑ns | 布线ns | 最大数据扇出 | slack ns |',
 '|---|---|---|---:|---:|---:|---:|---:|']
 x=v['dual_types_slide_admit']
 labels={'frontend':'前端出发','front_feedback':'前端头部反馈','wb_to_f1':'WB至副槽转发有效','mul_enable':'共享DSP使能','redirect':'重定向寄存器'}
 for k,label in labels.items():
  p=x['targeted_paths'][k][0]
  lines.append(f'| {label} | `{p["start"]}` | `{p["end"]}` | {p["logic_levels"]} | {p["logic_ns"]:.3f} | {p["route_ns"]:.3f} | {p["max_data_fanout"]} | {p["slack_ns"]:.3f} |')
 p=x['slow_setup_paths'][0]
 lines += ['', f'最终滑动版全局最差setup：`{p["start"]}` → `{p["end"]}`，{p["logic_levels"]}级、逻辑{p["logic_ns"]:.3f}ns、布线{p["route_ns"]:.3f}ns、slack{p["slack_ns"]:.3f}ns。DSP使能的冗余预测比较已删除，但原tag/操作数就绪/接收使能关系仍会进入共享DSP控制；不能把删除一个门控项称为切断整个控制网络。', '',
 '## 分布式RAM归因', '',
 '| 路由后映射 | 已采纳基线 | 最终组合admit | 最终滑动slide_admit |',
 '|---|---:|---:|---:|']
 from archive_dual_types import ram_counts
 brr=ram_counts(ROOT/'simulation/results/load_bp_dual_fwd_share/pds/place_route/top_pnr.netlist')
 for key,label in [('instruction_fifo','指令队列数据/元信息'),('adjacency_links','组邻接标志'),('btb','BTB'),('regfile','寄存器堆多读口副本'),('exmem_fifo','EX/MEM队列')]:
  lines.append(f'| {label} | {brr.get(key,0)} | {v["dual_types_admit"]["ram_breakdown"].get(key,0)} | {v["dual_types_slide_admit"]["ram_breakdown"].get(key,0)} |')
 lines += ['', '最终滑动版分布RAM比基线增加70：跨组读取使指令队列增加一个读副本（+64），邻接标志占2，原来部分常量的副槽分支/乘法结果位变为变量使EX/MEM净增4。分布RAM没有转占48个DRM，但会增加小RAM原语、互连与布局压力。采用路由netlist计数并与器件资源报告核对，未使用综合中剪枝前的738/804作为最终资源数。', '',
 '## 验证与证据', '',
 '- 9个不可变RTL候选，各通过63项架构/SoC/ISA检查、7项随机前端/寄存器堆/依赖与异常/计数检查、6项副槽定向差分检查；固定1次和10次两张CoreMark镜像均通过CRC、退休计数及参考行为核对。',
 '- 滑动定向程序每次覆盖64 taken、64 not-taken副槽分支、64副槽乘法及结果广播、63次双组弹出；另测不对齐分支精确异常、主槽load错误取消副槽以及恢复路径。随机前端每个种子100,000拍、寄存器堆每种子800,000次读检查，共3种子。',
 '- 所有候选无LATCH/UNOPTFLAT/MULTIDRIVEN/UNDRIVEN/IMPLICIT/PINMISSING/PINNOTFOUND危险lint告警。最后准入版保留供bench观察的完整译码输出，UNUSEDSIGNAL计数为49，未以屏蔽危险告警换通过。局部SAT日志包含准入合法性及简化译码证明。',
 '- 初期core smoke监视器局部变量与bench命名冲突，换新监视器/工具后完成回归；初版通用滑动微测因分组变化仅命中2次副槽不跳转，差分行为正确但覆盖门槛不足，新增专门滑动程序达到64次。初始诊断保留，不修改已通过RTL/工具来迁就结果。',
 '- 所有候选各做一次PDS路由及slow/fast setup/hold检查，没有seed sweep。所有定向STA使用各自已路由ADF，并对输入哈希核对。没有开发板、Flash、像素游戏或实际提频验证，CoreMark为短运行诊断。',
 '- 基线完整源/IP/证据哈希、原单发23个受保护源、正式STA、前四轮归档清单均核对不变；上一轮native候选仍为拒绝状态。候选前端来源监视器尚未适配滑动头部，故其front_origin字段不用于横向结论；来源分解只使用同RTL基准control。', '',
 '原始比较：`docs/dual_types/comparison.json`；每候选RTL、生成信息、回归、profile、PDS报告、定向STA与工具在同目录归档；9份ADF和9份路由netlist压缩存储并逐内容验证SHA256。`manifest.json`覆盖归档内每个文件，报告完成后生成。', '',
 '后续应先隔离跨组普通ALU收益与副槽乘法导致的提交等待，再处理前端配对反馈的扇出和路由；本轮没有继续堆叠准入类型或扩大等待网络。']
 (ROOT/'docs/dual_types.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print('WROTE docs/dual_types.md')

if __name__=='__main__':main()
