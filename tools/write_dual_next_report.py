"""Summarize measured independent IPC/frequency trials, without adopting a version."""
from pathlib import Path
import json,hashlib
from parse_dual_joint_timing import paths
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'docs/dual_next_trials'
LABELS={'mqual':'乘法旁路资格提前寄存','fqual':'F/F1/M旁路资格提前寄存','mpre':'主槽乘法提前启动','loadsplitv2':'主槽load先行、副槽ALU后执行','pairmul':'访存主槽＋乘法副槽','pairbranch':'访存主槽＋分支副槽','loadcapture':'load返回仅捕获到操作数寄存器','wordwake':'仅LW同拍返回旁路','loadwake':'完整load同拍返回旁路','aluwake':'整组ALU返回隔离对照','alulanes':'逐槽独立ALU返回隔离'}
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 DEST.mkdir(exist_ok=True);a=read(ROOT/'docs/accepted_dual_baseline.json');base=ROOT/a['source_directory'];ref=read(base/'performance/result.json');bc=a['coremark_stats_cycles'];bi=a['ipc'];rows={}
 for t in LABELS:
  src=ROOT/('simulation/results/load_bp_dual_boundary_next_'+t);x=read(src/'performance/result.json');pd=read(src/'pds/result.json');suite=read(src/'next_suite/result.json');assert suite['status']=='PASS',(t,suite)
  cycles=int(x['metrics']['Stats window cycles']);retired=int(x['metrics']['Retired instructions']);sec=x['dual']['secondary_retired'];ipc=retired/cycles
  rows[t]=dict(label=LABELS[t],variant='dual_boundary_next_'+t,cycles=cycles,retired=retired,ipc=ipc,ipc_gain_pct=(ipc/bi-1)*100,cycles_saved=bc-cycles,main_retire_rate=(retired-sec)/cycles,side_retire_rate=sec/cycles,metrics=x['metrics'],dual=x['dual'],joint=x['joint'],mem_ipc=x['mem_ipc'],next_trial=x['next_trial'],timing_status=pd['status'],estimated_fmax_mhz=pd['estimated_fmax_mhz'],resources=pd['resources'],corners=pd['corners'],paths=paths(src/'pds/report_timing/top.rtr'),estimated_ipc_fmax=ipc*pd['estimated_fmax_mhz'],checks=suite)
 eligible=[t for t,z in rows.items() if z['timing_status']=='PASS' and (z['ipc']>bi or (z['ipc']==bi and z['estimated_fmax_mhz']>a['estimated_fmax_mhz']))]
 preferred=max(eligible,key=lambda t:rows[t]['ipc']*80,default=None)
 result=dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',preferred_candidate=preferred,accepted_descriptor_sha256=sha(ROOT/'docs/accepted_dual_baseline.json'),accepted=a,candidates=rows,opportunity_probe=read(ROOT/'simulation/results/load_bp_dual_boundary_next_probe/performance/result.json')['next_trial'],note='Single identical physical flow per RTL, PLL80/12.500ns and same images; no seed search, constraint relaxation or board test. Fmax is an STA estimate, not validation at a lower operating clock. Original failed loadsplit retained separately; repaired v2 is the measured candidate.')
 (DEST/'comparison.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
 intro=('推荐保留隔离候选 `dual_boundary_next_'+preferred+'` 供用户评估；当前采纳描述符未修改。') if preferred else '本轮有效候选均不建议纳入当前80 MHz基线；已有采纳版保持不变。'
 s='# IPC与主频后续优化联合试验\n\n'+intro+'\n\n以采纳版 `dual_boundary_storewrite` 为共同起点；fqual只叠加本轮mqual，aluwake只叠加本轮capture-only，alulanes进一步将ALU返回资格按槽独立判断，均未混入此前拒绝的改动。各方案分别比较，没有把多个未验证策略合并后归因。\n\n'
 s+='## 同镜像性能、完整时序与资源\n\n| 版本 | fixed10周期 | IPC | IPC变化 | STA估算Fmax MHz | 慢角setup ns | 最差hold ns | LUT | FF |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|\n'
 entries=[('采纳基线',dict(cycles=bc,ipc=bi,ipc_gain_pct=0,estimated_fmax_mhz=a['estimated_fmax_mhz'],corners=a['corners'],resources=a['resources']))]+[(z['label'],z) for z in rows.values()]
 for label,z in entries:
  h=min(z['corners'][k]['worst_slack_ns'] for k in ('Hold Summary(Slow Corner)','Hold Summary(Fast Corner)'));setup=z['corners']['Setup Summary(Slow Corner)']['worst_slack_ns'];r=z['resources'];s+=f"| {label} | {z['cycles']:,} | {z['ipc']:.6f} | {z['ipc_gain_pct']:+.3f}% | {z['estimated_fmax_mhz']:.3f} | {setup:+.3f} | {h:+.3f} | {r['LUT']} | {r['FF']} |\n"
 s+='\n各版均为 **709分布式RAM、48 DRM、4 APM**；没有新增LSU、乘法器或指令FIFO容量。所有候选真实PLL均为80 MHz，约束12.500 ns，选项和器件一致，每版只做一次布局布线，没有扫seed、加false/multicycle path或放宽uncertainty。负setup仍是80 MHz失败，hold违例也单独计为失败。估算Fmax不能代替在另一频率的重新实现/验证；尤其loadsplitv2的hold违例不能靠降频或提频消除。\n\n'
 s+='## 逐拍机会与实际净收益\n\n原版110,515拍副槽单独等待分解为：主槽ALU37,234、load17,840、store1、乘法55,440拍。它们是发生等待的窗口，不是可相加的省拍。主槽普通ALU先算完不等于整组能够推进；本轮分别实现了可独立启动的主槽乘法，以及主槽load先进入原MEM、年轻ALU仍留在EX的分步执行。两者都沿用原tag/lane和原组的顺序提交。\n\n'
 z=rows['mpre'];s+=f"主槽乘法提前版，在基准窗口提前启动{z['next_trial']['early_mul']:,}次，副槽等待中主槽乘法由55,440降至{z['next_trial']['sidewait_mul']:,}拍；整核净省{z['cycles_saved']:,}拍、IPC提升{z['ipc_gain_pct']:.3f}%。但布线估算{z['estimated_fmax_mhz']:.3f} MHz，无法保留80 MHz。\n\n"
 s+='load分步版增加一个待完成副槽所有者、结果寄存和一次性响应保留。主槽先进入有序MEM，副槽算完后才允许原组退休，年轻组不能越过；定向程序确认分步路径确实触发。修正版fixed10周期完全不变，额外状态与MEM保留没有转化为本镜像的净吞吐收益。初版因旧token完成误清新所有者而少退休586条副槽指令，已被完整退休计数检查拒绝；修正版将清除限定到实际有效的旧所有者，重新通过整套回归。失败源码/生成器/日志保留，未混入有效结果。\n\n'
 for t in ('pairmul','pairbranch'):
  z=rows[t];s+=f"{z['label']}：净省{z['cycles_saved']:,}拍，IPC提升{z['ipc_gain_pct']:.3f}%，估算{z['estimated_fmax_mhz']:.3f} MHz。"
  if t=='pairmul':s+='响应保留命中'+f"{z['next_trial']['held_response']:,}次，已接受store但尚待乘法的保留命中{z['next_trial']['held_posted']:,}次；因此扩大准入需要真正处理两种不同完成时刻，不能只放宽类型条件。"
  s+='\n\n'
 z=rows['pairbranch'];s+=f"分支配对版副槽分支退休54,537→{z['joint']['branch']:,}，副槽单独等待110,515→{z['mem_ipc']['secondary_only']:,}拍，体现扩大配对也会增加成组等待。副槽有效退休率28.95%→{z['side_retire_rate']:.2%}，整核只净省5,910拍，不能把新增配对次数当成同等省拍。该版唯一功能改动为ID扩展准入：判断进入既有ID分配和FIFO pop1/pop2控制，由对应寄存边界捕获；未添加EX/MEM数据旁路或MEM ready反馈。已有跨模块控制路径仍保留。\n\n"
 s+='## load返回与跨模块路径\n\n完整返回旁路把LB/LBU/LH/LHU/LW格式化后的数据直接送到消费者，LW版只送未格式化整字。二者都能提高IPC，但都新增RAM输出到操作数选择、EX地址/分支运算及请求/恢复控制的组合通路。LW省去格式化并没有消除跨级数据路径。\n\n'
 s+='capture-only版只把返回值在现有操作数寄存器边沿捕获，当前拍EX可用性与选择不使用返回数据；它保持原IPC和周期，作为“寄存旁路”的时序对照。\n\n'
 z=rows['aluwake'];l=rows['alulanes'];s+=f"ALU隔离版增加独立ALU输入端口，返回数据只参与ALU结果，AGU、分支比较、跳转目标和CSR仍使用原来的寄存来源。局部SAT证明：任意新增ALU数据不会改变EX的ready/valid、分支决定、地址、异常、store数据或辅助字段；新增ALU口接回原操作数时与采纳版组合EX完全相同（证明配置关闭除法，完整含除法CPU另由回归验证）。整组ALU对照IPC为{z['ipc']:.6f}、提升{z['ipc_gain_pct']:.3f}%；进一步去掉“伴随指令也必须是ALU”的非必要限制，逐槽独立开放ALU返回后IPC为{l['ipc']:.6f}、提升{l['ipc_gain_pct']:.3f}%。后一版EX字节完全相同，明确按哈希复用局部SAT证据，独立重跑本版操作数模型、整核回归和真实SoC。\n\n两版都避免了完整返回版同拍返回数据进入AGU/分支计算的设计连接，但返回有效资格到执行/请求控制的路径仍存在，不能称为消除了所有长控制链。它们与完整返回版的差距还包含成组供给和等待时序的变化，不能直接将IPC差值归属为某一种load→分支或load→load的独立收益。\n\n"
 p=rows['alulanes']['paths'][0];s+=f"逐槽ALU版最终全局最差转到`{p['start']}`→`{p['end']}`，{p['logic_levels']}级，逻辑{p['logic_ns']:.3f} ns、布线{p['route_ns']:.3f} ns。因此，即使所查RAM B口到控制端的路径被隔开，也不能据此宣布整核80 MHz通过。\n\n"
 s+='输入信用始终来自寄存队列占用，没有新增MEM ready到EX输入信用的组合反馈。所有候选的完整最差路径如下；沿途最大扇出不能代替源寄存器总扇出，也不能把布线增加全归因于扇出。\n\n| 版本 | 全局最差起点→终点 | 级数 | 逻辑/布线 ns | 路径最大数据扇出 |\n|---|---|---:|---:|---:|\n'
 for t,z in rows.items():
  p=z['paths'][0];s+=f"| {t} | `{p['start']} → {p['end']}` | {p['logic_levels']} | {p['logic_ns']:.3f}/{p['route_ns']:.3f} | {p['max_data_fanout']} |\n"
 s+='\n定向查询另外覆盖IF/操作数寄存边界、操作数到控制端，以及RAM B口到redirect/F/F1有效位/RAM使能。后者为空只表示指定物理端点集合没有报告匹配路径，不替代全核形式证明。\n\n| 查询版本 | IF/操作数边界最差setup ns | 操作数→控制最差setup ns | RAM B口→所查控制端 |\n|---|---:|---:|---|\n'
 for t in ('storewrite','next_pairbranch','next_aluwake','next_wordwake','next_alulanes'):
  qp=ROOT/('simulation/results/load_bp_dual_boundary_'+t+'/next_paths/result.json')
  if not qp.exists():continue
  q=read(qp)['paths'];rp=q['ram_b_control'];s+=f"| {t} | {q['id_boundary'][0]['slack_ns']:+.3f} | {q['operand_control'][0]['slack_ns']:+.3f} | "+(f"{rp[0]['slack_ns']:+.3f} ns / {rp[0]['logic_levels']}级" if rp else '无匹配路径')+' |\n'
 s+='\n旁路资格试验减少了一些映射逻辑，但M-only及F/F1/M版的全局路径仍落在既有等待/来源选择到请求使能的网络上；局部删门没有形成整核提频。\n\n## 双发有效利用率\n\n“主/副槽利用率”以下均为退休条数除以同一统计窗口周期，不与含投机的发射组数混用。\n\n| 版本 | 主槽有效退休/周期 | 副槽有效退休/周期 | 发射双发组/全部组 |\n|---|---:|---:|---:|\n'
 s+=f"| 采纳版 | {(a['retired']-a['dual']['secondary_retired'])/bc:.2%} | {a['dual']['secondary_retired']/bc:.2%} | {a['dual']['pairs_issued']/a['dual']['groups_issued']:.2%} |\n"
 for t,z in rows.items():s+=f"| {t} | {z['main_retire_rate']:.2%} | {z['side_retire_rate']:.2%} | {z['dual']['pairs_issued']/z['dual']['groups_issued']:.2%} |\n"
 s+='\n## 验证范围和取舍\n\n每个有效候选均通过fixed1/fixed10 CRC、相同架构退休总数、63项整核/随机/ISA、6项配对、4项取消、4项lint/结构/准入审计、8项未来tag、4项乘法tag、6项真实posted-enabled SoC契约、4项逐拍load及真实top UART80帧检查。\n\nM资格、F/F1/M资格、capture-only、LW返回、完整返回和独立ALU返回另各运行300,000拍操作数模型；前两者使用真实下一拍valid契约，capture-only使用返回值下一拍成为相同WB值的契约，独立ALU版本比较其有效独立ALU数据口。没有将局部模型称为整核形式证明。\n\n扩展配对、主槽提前乘法、load分步版还运行新增访存配对/分步与精确异常定向程序，在带随机响应延迟的core及真实SoC上检查，覆盖主槽load/store故障时副槽不得退休和故障前的预测重定向。新增响应保留模块对POST_LOCAL_STORES=0/1分别检查128组load、随机等待与token重用、错误保留、取消；配对乘法另各覆盖32组store，已有8项posted-store模块测试也重新运行。\n\n所有有效RTL/IP生成器精确重建，编译输入哈希与采纳版描述符/源文件/IP/证据核验。Verilator对LW性能编译曾出现一次内部错误，保留失败日志，原源码不变重跑通过；还有模块证明输入缺少divider依赖及适配器结果目录名称的问题，修正工具后通过，未修改CPU去绕过断言。\n\n'
 s+='ALU返回版逐拍测试原先沿用“所有消费者均在WB下一拍执行”的旧预期，保留失败记录后，按“ALU返回当拍、LSU下一拍”的精确契约重新检查已经运行的真实SoC波形；未放宽为任意等待，也未修改RTL。\n\n'
 s+='软件镜像仍打印75 MHz，旧软件把IPC>1提示为不可用；本报告使用独立退休/周期窗口。短CoreMark仅作诊断，不是正式成绩；本轮没有上板，没有验证游戏负载。\n\n'
 cleanup=ROOT/'simulation/cleanup_dual_next_trials_result.json'
 if cleanup.exists():
  c=read(cleanup);s+=f"本轮新增的可重建obj/VVP/PDS compile/STA查询DB缓存已清理，共{c['files']:,}文件、{c['bytes']:,}字节（约{c['bytes']/1024**3:.3f} GiB）。RTL/IP、镜像、日志、trace、STA、映射资源报告及压缩路由快照保留，采纳版描述符哈希未变。\n\n"
 s+=('建议保留上述推荐候选供进一步评估。' if preferred else '建议维持现有采纳版。扩大准入的净收益较小，直接返回旁路的IPC收益不足以抵消本次主频代价；后续若继续，应先测清切断操作数到请求控制路径所需的寄存边界及其等待代价，再选择是否以少量IPC换更高频率。')+'\n\n完整机器数据见[comparison.json](dual_next_trials/comparison.json)，归档哈希见[manifest.json](dual_next_trials/manifest.json)。\n'
 (ROOT/'docs/dual_next_trials.md').write_text(s,encoding='utf-8');print('REPORT preferred',preferred)
if __name__=='__main__':main()
