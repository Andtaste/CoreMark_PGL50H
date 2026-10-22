"""Render the measured joint-design report without promoting research RTL."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
 c=read(ROOT/'docs/dual_joint/comparison.json');v=c['candidates'];b=read(ROOT/'simulation/results/load_bp_dual_fwd_share/performance/result.json');bp=c['baseline_pds'];best=c['preferred_research_candidate'];final=v['dual_joint_reg'];fixed=v['dual_joint_fix'];bc=int(b['metrics']['Stats window cycles']);ret=int(b['metrics']['Retired instructions'])
 lines=['# 滑动供给、双槽旁路与配对准入联合设计', '', '2026-10-21。隔离研究完成，尚未采纳。当前正式采纳描述仍为 `dual_fwd_share`；未改正式源、单发对照、固件、PLL或开发板。用户允许旁路带来一定长路径，评价同时看实际周期、估计频率、资源与路径。', '',
 '## 结论', '',
 f'推荐研究候选由通过功能与时序且按Fmax折算吞吐有正收益的版本中选择：`{best}`。最终寄存匹配版 IPC={final["ipc"]:.6f}，同频吞吐变化{final["same_clock_gain_percent"]:+.3f}%，估计Fmax={final["estimated_fmax_mhz"]:.3f}MHz，按各自Fmax折算吞吐变化{final["estimated_peak_gain_percent"]:+.3f}%。同频收益在当前约75MHz PLL配置下也适用，但尚无板上实测。', '',
 '最终版副槽有效退休利用率从5.368%升至24.820%，主槽从75.826%变为65.922%；主槽比例下降是更多指令移入副槽，合计IPC上升。发射时双发比例从7.168%升至38.448%。这两个比例不能混用：24.820%的分母为全部周期，38.448%的分母为主槽发射次数。', '',
 '直接比较修正版本次估计79.942MHz，寄存匹配版79.133MHz，实测性能选择前者；后者缩短部分匹配控制路径，但瓶颈转移到前端，未提高本次全局频率。每份RTL各一次路由包含布局差异，不能据此断言寄存匹配必然更慢。两个版本均只保留为研究候选。', '',
 '## 结构', '',
 '- 供给：保留四个取指组、最多八条的原存储及64位取指宽度，缓存下一组低半条并携带已寄存邻接标志。单发消耗一条、双发两条、阻塞零条；跨组可同时弹出两个单条组。信用仅看已寄存占用/预留，不由当拍pop贯通到取指请求准备。该缓存方案并非上轮被拒绝的原生逐条FIFO重写。',
 '- 旁路：保留主槽A/B队列逻辑，为副槽C/D记录最年轻生产者的4位组/槽tag及等待位；使用原224位side packet内的64位操作数空间捕获数据，没有另外增加C/D数值数组。入队可捕获当拍已寄存广播；阻塞期间继续保存F、F1、M、W、W1结果。需要等待的较老ALU/load/MUL/DIV均可进入原两项队列，不因其尚未退休直接拆对。',
 '- 准入：普通ALU副槽、普通ALU主槽+副槽条件分支、普通ALU主槽+共享乘法、预测不跳转的主槽条件分支+普通ALU副槽。仍拒绝同组RAW/WAW，允许WAR；不支持同组主槽结果立即供副槽使用。JAL/JALR、副槽LSU和除法未开放，同组最多一个条件分支和一次乘法。',
 '- 主槽分支若实际改道则取消副槽，保留组内精确提交顺序。寄存branch_redirect同步清除该组已取消副槽的目的寄存器记账，正确路径重新准入前完成取消；副槽条件分支仍携带自己的预测/实际下一PC。',
 '- 最终版提前一拍比较下一次将被寄存的F/M/W生产者身份，选择位经过FF，当前真正的valid/data授权执行。M身份包括槽位，低/高乘法完成路径都检查；不从LSU ready推测完成，不把原始RAM数据送入EX。插入时的当拍广播捕获仍用真实当前tag比较，停顿时不会丢失短暂广播。',
 '- 两个ALU、一个LSU、一套共享流水乘法器、八组顺序记账、两项ID/EX、249位四深度EX/MEM均保留；MEM ready仍在寄存credit边界终止。副槽执行器的除法器在综合展开时明确关闭。', '',
 '## 性能、时序与资源', '',
 '同一固定10次CoreMark镜像，各版退休2,808,261条、load548,709、store143,410、BJP571,070，五项CRC一致。IPC由精确计数重算。每份不可变RTL只做一次相同选项PDS实现，没有seed sweep。', '',
 '| 版本 | 窗口周期 | IPC | 同频吞吐变化 | 估计MHz | 各自Fmax吞吐变化 | LUT | FF | 分布RAM | 判定 |',
 '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|',
 f'| 已采纳基线 | {bc:,} | {ret/bc:.6f} | — | {bp["estimated_fmax_mhz"]:.3f} | — | 8,339 | 4,096 | 705 | PASS |']
 names={'ready':'滑动+仅已有广播准入','wait':'滑动+四源捕获等待+副槽分支/乘法','branch':'主槽分支初版，仅诊断','fix':'主槽分支取消修正版，直接比较','reg':'完整组合，寄存身份比较'}
 for suffix,label in names.items():
  x=v['dual_joint_'+suffix];r=x['resources'];status='功能失败，排除' if x['functional_status']!='PASS' else x['timing_status']
  lines.append(f'| {label} | {x["cycles"]:,} | {x["ipc"]:.6f} | {x["same_clock_gain_percent"]:+.3f}% | {x["estimated_fmax_mhz"]:.3f} | {x["estimated_peak_gain_percent"]:+.3f}% | {r["LUT"]:,} | {r["FF"]:,} | {r["Distributed RAM"]} | {status} |')
 lines += ['', '全部版本DRM48、APM4。仅已有广播准入版slow setup −0.479ns、178个失败端点；两角hold均通过，失败原因是setup。主槽分支初版虽通过CoreMark和PDS，但SoC随机测试死等已取消副槽的结果，不能作为有效候选。后两版修复并通过全部回归。', '',
 f'直接比较版需要至少{fixed["break_even_fmax_mhz"]:.3f}MHz才能追平原基线；实测估计{fixed["estimated_fmax_mhz"]:.3f}MHz。最终寄存比较版与修正版在两张镜像下的完整metrics/dual/joint/predictor/multiply计数逐项相同，说明比较前移没有增加等待或改变采样窗口。', '',
 '| 最终版四角 | 最差slack ns | 失败端点 |', '|---|---:|---:|']
 for k,x in final['corners'].items():lines.append(f'| {k} | {x["worst_slack_ns"]:.3f} | {x["failing_endpoints"]} |')
 lines += ['', '## 槽位利用与等待', '',
 '| 统计 | 已采纳基线 | 完整组合 |', '|---|---:|---:|',
 f'| 主槽发射 | {b["dual"]["groups_issued"]:,} | {final["dual"]["groups_issued"]:,} |',
 f'| 副槽发射 | {b["dual"]["pairs_issued"]:,} | {final["dual"]["pairs_issued"]:,} |',
 f'| 副槽退休 | {b["dual"]["secondary_retired"]:,} | {final["dual"]["secondary_retired"]:,} |',
 f'| 主槽每周期退休比例 | 75.826% | {final["occupancy"]["primary_retire_percent"]:.3f}% |',
 f'| 副槽每周期退休比例 | 5.368% | {final["occupancy"]["secondary_retire_percent"]:.3f}% |',
 f'| 主槽发射时双发比例 | 7.168% | {final["occupancy"]["pair_given_primary_issue_percent"]:.3f}% |',
 f'| 副槽占全部退休指令 | 6.612% | {final["occupancy"]["secondary_instruction_share_percent"]:.3f}% |', '',
 '最终版副槽退休构成为普通ALU674,147、条件分支67,324、乘法26,640；其中主槽条件分支搭配副槽成功退休86,415组。实际跨原取指组发射318,397次、同时弹出两组4,869次；485,489个发射配对的副槽引用了较老生产者。主槽发射却没有第二条从1,397,635次减到372,236次。', '',
 '依赖拆对计数归零只说明把相关指令放入队列等待，不表示真实依赖消失。EX操作数等待从588,971升至813,816，ID阻塞从650,132升至863,823，MEM占用从65,160升至110,880，乘法队首等待从37,880升至83,160；这些事件可能重叠，不能相加作为总耗时。总窗口仍减少363,920周期，说明收益超过新增等待。', '',
 '预测解决数571,070、方向错58,351、目标错3,642、下一PC错61,993均不变；BTB命中从510,904到510,844，副槽/主槽配对改变了取指与训练相位，不宣称逐项预测profile完全相同。没有换镜像、预测器容量或计数分母来制造收益。', '',
 '## 长路径与寄存比较边界', '',
 '允许旁路增加路径后仍逐项测量。直接比较等待版全局最差为F tag→共享DSP使能，15级逻辑、4.518ns逻辑+7.141ns布线；这是补充寄存身份比较版的直接原因。最终版仍有跨模块路径，未宣称全部切断。', '',
 '| 最终寄存比较版路径 | 起点 | 终点 | 级数 | 逻辑ns | 布线ns | 最大数据扇出 | slack ns |',
 '|---|---|---|---:|---:|---:|---:|---:|']
 labels={'frontend':'前端出发','front_feedback':'头部反馈','wb_to_f1':'WB到副槽广播有效','mul_enable':'DSP使能','redirect':'重定向','side_ready':'副槽tag/等待位','selector_input':'身份比较FF输入','selector_output':'身份比较FF输出'}
 for k,label in labels.items():
  p=final['targeted_paths'][k][0];lines.append(f'| {label} | `{p["start"]}` | `{p["end"]}` | {p["logic_levels"]} | {p["logic_ns"]:.3f} | {p["route_ns"]:.3f} | {p["max_data_fanout"]} | {p["slack_ns"]:.3f} |')
 p=final['slow_setup_paths'][0]
 lines += ['', f'最终版全局最差：`{p["start"]}` → `{p["end"]}`，{p["logic_levels"]}级，逻辑{p["logic_ns"]:.3f}ns、布线{p["route_ns"]:.3f}ns、slack{p["slack_ns"]:.3f}ns。输入侧/输出侧定向STA和真实CPU未来/当前tag逐拍检查共同验证新增FF边界，当前valid授权路径仍需独立评价。', '',
 '## 资源与冗余检查', '',
 f'最终版相对基线增加LUT {final["resources"]["LUT"]-8339:,}、FF {final["resources"]["FF"]-4096:,}、分布RAM70。直接比较修正版到寄存比较版：LUT变化{final["resources"]["LUT"]-fixed["resources"]["LUT"]:+,}、FF变化{final["resources"]["FF"]-fixed["resources"]["FF"]:+,}；寄存比较并非免费，但保留全部周期收益。', '',
 '| 路由后分布RAM归因 | 最终数量 | 相对基线 |', '|---|---:|---:|',
 '| 指令队列读副本 | 128 | +64 |', '| 邻接标志 | 2 | +2 |', '| BTB | 174 | 0 |', '| RF多读口副本 | 256 | 0 |', '| EX/MEM | 215 | +4 |', '',
 '没有新C/D数值RAM、第二LSU、第二乘法器、重复寄存器堆或BTB。控制/结果字段复用原side packet，避免扩宽EX/MEM；源tag依然编码后比较，没有恢复曾被拒绝的入槽去编码方案。局部SAT核对实际预译码合法性、side写目的、简化branch/MUL识别，显式关闭第二除法器。分布RAM统计来自路由netlist，并和器件资源报告核对。', '',
 '## 验证与失败处理', '',
 '- ready/wait/fix/reg各63项架构/SoC/ISA检查、7项前端/RF/依赖/异常/计数补充检查、6项副槽分支/乘法/滑动/精确异常定向差分检查；固定1次和10次CoreMark均CRC及独立计数通过。随机前端3×100,000拍，RF总计2,400,000次读比较。',
 '- ready/wait/fix的操作数RTL字节完全相同，共享一次3×100,000拍、600,000次边沿比较证据；reg另测同等随机规模。参考使用独立C/D数值存储和当前tag直接比较，覆盖入队命中、停顿捕获、重复广播优先级及清空。不是把同一实现复制后自比。',
 '- reg完成4份真实CPU程序×2个延迟种子的未来/当前F/M/W tag身份协议检查，另用四种乘法及交错低/高乘法、共享副槽乘法定向程序×2种子核对M标签槽位与退休轨迹。',
 '- fix/reg额外4份快速SoC程序逐拍检查分支取消目的记账、旁路来自副槽与正确路径退休，覆盖190次主槽分支取消副槽。副槽两个源的生产者按循环年龄独立核对最年轻写者，覆盖WAW年龄、槽位、队列复用。',
 '- 原型branch在SoC random_17超时；诊断保留，找到的等待PC0x838源指向已经取消的group2/lane1。修复写入新目录，未修改已通过的RTL或用CoreMark通过掩盖架构失败。',
 '- 所有合格候选无LATCH/UNOPTFLAT/MULTIDRIVEN/UNDRIVEN/IMPLICIT/PINMISSING/PINNOTFOUND危险lint告警。最终UNUSEDSIGNAL48，来自保留的观察接口等；未新增告警屏蔽来获取通过。局部SAT不是整核时序形式证明。',
 '- 初次ready定向报告收集器仅支持Slack(MET)，遇到负裕量时报错；新增支持MET/VIOLATED的解析器重读同一组报告，未重新路由或丢弃负值。正式ready状态仍明确TIMING_FAILED。',
 '- 原单发源/STA、已采纳双发源/IP/证据、前五轮不可变归档均校验不变；被拒绝的native/types候选未自动采纳。最终对比和报告完成后建立独立manifest，五份ADF和五份netlist压缩逐内容核对哈希。', '',
 '完整机器数据位于 `docs/dual_joint/comparison.json`，RTL/工具/仿真/路由/定向路径及失败诊断均在同目录归档。各实现仅一次PDS，实际PLL约75MHz，未做开发板或游戏应用验证。']
 (ROOT/'docs/dual_joint.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');print('WROTE docs/dual_joint.md')
if __name__=='__main__':main()
