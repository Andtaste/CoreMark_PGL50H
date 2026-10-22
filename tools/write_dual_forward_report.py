"""Write measured forwarding/control timing results without changing baseline."""
from pathlib import Path
import json,sys
from parse_dual_joint_timing import paths
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 a=read(ROOT/'docs/accepted_dual_baseline.json');names=['dual_boundary_'+s for s in ('headmux','pcselect','headlocal')];labels={'dual_boundary_storewrite':'已采纳 storewrite','dual_boundary_headmux':'headmux：队首选择并入源选择','dual_boundary_pcselect':'pcselect：提前准备下一 PC 候选','dual_boundary_headlocal':'headlocal：局部队首指针复制'}
 rows={'dual_boundary_storewrite':a}
 for n in names:rows[n]=read(ROOT/('simulation/results/load_bp_'+n+'/pds/result.json'))
 chosen=max((n for n in names if rows[n]['status']=='PASS' and rows[n]['estimated_fmax_mhz']>a['estimated_fmax_mhz']),key=lambda n:rows[n]['estimated_fmax_mhz'],default=None)
 intro=('本轮推荐保留隔离候选 `'+chosen+'` 供采纳，当前描述符尚未改动。') if chosen else '本轮没有取得整核提频收益，三版均不建议合入，当前采纳基线保持不变。'
 s='# 旁路选择到控制端的路径与扇出优化\n\n'+intro+'\n\n上轮 `bankreq`、`banklocal`、`wbflags` 已被用户明确拒绝。本轮三版各自独立从已采纳 `dual_boundary_storewrite` 生成，没有叠加上轮改动，也没有将本轮三个方向组合。目标是保持周期和执行语义不变，评估实际控制路径及物理扇出。\n\n'
 s+='| 版本 | 估算 Fmax MHz | 慢角 setup ns / 失败端点 | 最差 hold ns | LUT | FF |\n|---|---:|---:|---:|---:|---:|\n'
 for n,x in rows.items():
  c=x['corners'];z=c['Setup Summary(Slow Corner)'];h=min(c['Hold Summary(Slow Corner)']['worst_slack_ns'],c['Hold Summary(Fast Corner)']['worst_slack_ns']);r=x['resources'];s+=f"| {labels[n]} | {x['estimated_fmax_mhz']:.3f} | {z['worst_slack_ns']:+.3f} / {z['failing_endpoints']} | {h:+.3f} | {r['LUT']} | {r['FF']} |\n"
 s+='\n所有版本保持 **709 分布 RAM / 48 DRM / 4 APM**。采用真实独立 PLL80、12.500 ns、多角 setup/hold；每个候选只做一次相同选项物理实现，没有扫种子或放宽约束。负 setup 余量仍计为失败。尚未上板。\n\n## 三个方向与实际代价\n\n'
 s+='`headmux` 仅改 `nc_operands`。原来先为两个物理槽分别完成 32 位旁路选择，再取队首；候选把队首选择分配到原有的互斥源选择条件，广播数据通过共享 OR 网络。各槽原有捕获、F > F1 > M > W > W1 优先级、无数据可用时的输出及握手全部保持。完整时序等价不依赖“重复广播数值相等”的假设。\n\n'
 s+='这项改写扩大了控制掩码和队首指针负载：乘法广播有效位的直接扇出从 31 降到 24，但队首指针从 829 升到 1117；LUT 增加 400，整核仅 79.308 MHz。这说明把宽数据多路器展开为掩码 OR，并不必然减少实际电路或降低关键扇出。\n\n'
 s+='`pcselect` 仅改 `nc_execute`。用已寄存指令类别提前准备固定下一 PC、分支跳转和顺序候选，晚到的 taken 只选择分支候选；原有异常、预测、除法、握手与辅助字段不变。完整 EX 在 ENABLE_DIV=0/1 两种配置均证明时序等价，但布局布线为 78.995 MHz，增加 76 LUT。不能用局部代数层次变化代替整核收益。\n\n'
 s+='`headlocal` 再次直接从采纳基线出发，保留原来的数据选择结构，仅增加六个与原 rd 在同一边沿捕获、下一状态相同的局部指针，分别驱动主槽元数据、副槽元数据和四个操作数输出多路器。原 rd 继续负责占用和可用性控制；没有多等一拍。PDS 的 preserve 属性用于防止这些有意分担负载的复制被合并，综合网表实际保留六个 GTP_DFF。它们是明确计入资源的负载分区成本，不能称为删除冗余。\n\n'
 s+='该版映射资源增加 41 LUT、6 FF；全局最差转为 `wb_v → memory_queue/data_177/WD`，逻辑 4.103 ns、布线 9.200 ns，另有 `wb_v → redirect_pc[9]` 为 −0.741 ns。即使指针负载确实被分散，本次全局 Fmax 仍降到 75.250 MHz。这里的失败包含原有 WB 资格、旁路和后级写入路径的布局变化，不能将单条指针网的改善等同于整核改善。每版仅一次实现，结论限于本轮实测。\n\n'
 q={n:read(ROOT/'simulation/results/dual_forward_control_paths'/n/'result.json')['paths'] for n in rows}
 s+='## 同一组 STA 查询的对照\n\n下表中广播扇出取该 FF 的 Q 后第一条实际数据网；队首值为原指针或六个局部复制中的最大直接扇出。它们与整条路径上的最大扇出分开记录，避免混用。\n\n| 版本 | 乘法广播 valid 直接扇出 | 队首指针最大直接扇出 | 乘法广播→控制余量 ns / 级数 | 已寄存匹配→控制余量 ns / 级数 |\n|---|---:|---:|---:|---:|\n'
 for n in rows:
  z=q[n];m=z['multiply_control'][0];c=z['match_control'][0];head=z['head_control'][0]['start_data_fanout']
  if n.endswith('headlocal'):head=max(z['pointer_'+str(i)][0]['start_data_fanout'] for i in range(6));head=max(head,z['pointer_original'][0]['start_data_fanout'])
  s+=f"| {labels[n]} | {m['start_data_fanout']} | {head} | {m['slack_ns']:+.3f} / {m['logic_levels']} | {c['slack_ns']:+.3f} / {c['logic_levels']} |\n"
 s+='\n“控制端”查询固定覆盖 redirect/redirect_pc、f_valid、f1_valid。每组取其最差路径；起终点可能随优化变化，详细路径和逻辑/布线/沿途最大扇出均在冻结 JSON 与 RTR 中保留。headlocal 查询额外覆盖复制指针，并逐个查询七个实际指针，未只统计变轻的原 rd。\n\n'
 if 'pointer_0' in q[names[-1]]:
  vals={k:q[names[-1]][k][0]['start_data_fanout'] for k in ['pointer_original']+['pointer_'+str(i) for i in range(6)]};s+='headlocal 的七条指针直接扇出为 `'+json.dumps(vals)+'`。\n\n'
 s+='| 版本 | 实际全局最差路径 | 逻辑级数 | 逻辑 / 布线 ns | 沿途最大数据扇出 |\n|---|---|---:|---:|---:|\n'
 for n in rows:
  p=paths(ROOT/('simulation/results/load_bp_'+n+'/pds/report_timing/top.rtr'))[0];start=p['start'].split('/opit')[0];end=p['end'].split('/opit')[0];s+=f"| {labels[n]} | `{start} → {end}` | {p['logic_levels']} | {p['logic_ns']:.3f} / {p['route_ns']:.3f} | {p['max_data_fanout']} |\n"
 s+='\n这些改写没有添加 MEM ready 到 EX 准入的新组合反馈，没有新增原始 RAM 数据旁路，也没有改变负载返回、乘法交接或配对类型。已有“寄存匹配/广播 → 源选择 → EX 运算/分支比较 → 控制寄存器或请求使能”的路径仍存在；局部扇出下降不等于切断跨模块链。不能宣称本轮消除了长链。\n\n'
 s+='## 性能与验证\n\n三版 fixed10 均为 **2,704,650 周期 / 2,808,261 退休 / IPC 1.0383084687**，fixed1 均为 271,550 周期 / 280,944 退休。完整 metrics、预测、乘法、双发、边界、MEM 等待、load 队列及 store 后继计数均与采纳版一致；生成器重建的 RTL/PLL/RAM 哈希一致。\n\n'
 s+='headmux 与 headlocal 分别对完整实际 operand 模块做时序归纳等价，覆盖任意广播、冲突优先级、暂停、插入、清空和复位；pcselect 对完整实际 EX 做有/无除法两配置等价。每版独立运行 63 项整核/随机/ISA、6 项配对、4 项取消、4 项 lint/结构/准入审计、8 项生产者 tag 协议、4 项乘法协议、6 项启用 posted-store 的真实 SoC、4 项逐拍和真实 top UART80 全帧检查。MEM 字节完全未改，默认 MEM 与 posted-store 模块证据通过明确的来源哈希复用，未声称重新运行。\n\n'
 s+='配对测试使用已有 v3 的 held-slot 观测器。试验最初误调用旧观测器时，其输入包与当前 MEM 所有权不一致造成断言失败；随后用原有修正版重跑通过，候选 RTL 未因此修改。汇总脚本也修正了默认 MEM 历史证据的目录定位，已经通过的测试只重新收集校验，没有为归档重复仿真。\n\n'
 s+='软件镜像仍保留 75 MHz 打印元数据及旧版 IPC>1 检查，表中 IPC 以退休/周期独立计算；短仿真不作为正式 CoreMark 得分。原生产单发 STA、当前采纳描述符/源码/IP/证据以及六组既有冻结归档均核验保持不变。\n\n'
 c1=read(ROOT/'simulation/cleanup_dual_forward_control_result.json');c2=read(ROOT/'simulation/cleanup_dual_head_local_result.json');s+=f"仅删除本轮六个可重建 Verilator obj 缓存，共 {int(c1['bytes']+c2['bytes']):,} 字节；源码、固件、日志、trace、STA 和路由快照保留。\n\n"
 s+='完整记录见 [冻结比较](dual_forward_control/comparison.json)、[哈希清单](dual_forward_control/manifest.json) 和 [定向 STA](dual_forward_control/selected_paths/)。当前正式采纳状态仍以 [采纳描述符](accepted_dual_baseline.json) 为准。\n'
 (ROOT/'docs/dual_forward_control.md').write_text(s,encoding='utf-8');print('REPORT',chosen)
if __name__=='__main__':main()
