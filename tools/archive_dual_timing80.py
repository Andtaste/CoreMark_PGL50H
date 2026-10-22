"""Freeze every timing trial, with independent functional and routed evidence."""
from pathlib import Path
import hashlib,json,shutil,zipfile,re
from parse_dual_joint_timing import paths
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'docs/dual_timing80';NAMES=['dual_boundary_'+s for s in ('clock','side','pair','uart','slots')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def main():
 assert not (DEST/'manifest.json').exists();DEST.mkdir(exist_ok=True);accepted=ROOT/'docs/accepted_dual_baseline.json';a=read(accepted);assert a['variant']=='dual_boundary_launch'
 for key in ('source_sha256','ip_sha256','evidence_sha256'):
  for n,h in a[key].items():assert sha(ROOT/n)==h,(key,n)
 for key,n in (('single_issue_reference_sha256','docs/accepted_baseline.json'),('single_issue_sta_sha256','hardware/pds/report_timing/top.rtr')):assert sha(ROOT/n)==a[key]
 prior={}
 for name in ('dual_fwd','dual_fan','dual_admit','dual_native','dual_types','dual_joint','dual_split','dual_legacy','dual_lsu','dual_boundary'):
  m=read(ROOT/'docs'/name/'manifest.json')
  for n,h in m.items():assert sha(ROOT/'docs'/name/n)==h,(name,n)
  prior[name]=len(m)
 def verify(x,label):
  for key in ('input_sha256','actual_compile_sha256','ip_sha256'):
   for n,h in x.get(key,{}).items():
    p=ROOT/n
    if not p.exists() and n.replace('\\','/').startswith('tmp/'):p=ROOT.parent/n
    assert p.is_file() and sha(p)==h,(label,n)
    # Share sources, images, tools and reference result metadata once.
    if not any(('load_bp_'+v) in n for v in NAMES) and p.suffix!='.adf':copy(p,DEST/'inputs'/n)
 rows={};counts={}
 for name in NAMES:
  src=ROOT/('simulation/results/load_bp_'+name);g=read(src/'generation.json');verify(g,name);assert g['accepted_dual_sha256']==sha(accepted)
  gen='generate_dual_timing80'+('_pair' if name.endswith('_pair') else '_uart' if name.endswith('_uart') else '_slots' if name.endswith('_slots') else '')+'.py';assert sha(ROOT/'tools'/gen)==g['generator_sha256']
  for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
  statuses={}
  for p in src.rglob('result.json'):
   if 'obj' in p.parts:continue
   x=read(p);verify(x,str(p.relative_to(ROOT)))
   if p.parent.name!='pds':assert x['status']=='PASS',p
   statuses[str(p.parent.relative_to(src))]=dict(status=x['status'],tests=len(x.get('tests',[])))
  pd=read(src/'pds/result.json');sim=read(src/'performance/result.json');assert pd['pds_exit_code']==0 and sha(src/'pds/run.tcl')==pd['tcl_sha256']
  text=(src/'pds/report_timing/top.rtr').read_text(errors='replace');assert re.search(r'12\.500\s+\{0 6\.25\}',text),name
  assert sim['metrics']['Stats window cycles']=='2807614' and sim['metrics']['Retired instructions']=='2808261'
  if name.endswith(('_side','_pair','_slots')):
   for sub,count in (('checks',63),('dual_checks',7),('pair_checks',6),('cancel_checks',4),('audit_checks',4),('timeline_checks',4),('memory_checks',4),('address_contract',10),('protocol',8),('mul_protocol',4)):
    assert statuses[sub]['tests']==count,(name,sub,statuses[sub])
  if name.endswith('_uart'):assert statuses['integration']['status']=='PASS' and statuses['uart80']['status']=='PASS'
  cycles=int(sim['metrics']['Stats window cycles']);ret=int(sim['metrics']['Retired instructions']);rows[name]=dict(timing_status=pd['status'],requested_mhz=80,estimated_fmax_mhz=pd['estimated_fmax_mhz'],resources=pd['resources'],corners=pd['corners'],cycles=cycles,retired=ret,ipc=ret/cycles,secondary_retired=sim['dual']['secondary_retired'],global_paths=paths(src/'pds/report_timing/top.rtr'),checks=statuses)
  if (src/'timing_paths/result.json').exists():rows[name]['selected_paths']=read(src/'timing_paths/result.json')['paths']
  for p in src.rglob('*'):
   if not p.is_file():continue
   rel=p.relative_to(src)
   if 'obj' in rel.parts or p.suffix in ('.vvp','.elf','.bin','.o','.exe','.pyc'):continue
   if rel.parts[0]=='pds' and rel.as_posix() not in ('pds/result.json','pds/run.tcl','pds/build.log','pds/report_timing/top.rtr','pds/device_map/top.dmr','pds/place_route/top.prr','pds/synthesize/apm_drm_lutram_utilization.log'):continue
   if rel.parts[0]=='timing_paths' and len(rel.parts)>2:continue
   copy(p,DEST/name/rel)
  counts[name]=statuses
  if name.endswith('_slots'):
   assert statuses['operand_checks']['tests']==3 and statuses['uart80']['status']=='PASS'
   assert read(src/'operand_checks/result.json')['cycles']==300000
   rows[name]['operand_evidence']=dict(actual_sha256=sha(src/'nc_operands.v'),evidence='operand_checks/result.json',inherited_reused_operand_sha256=g.get('reused_operand_sha256'),reuses_old_operand_test=False,note='Inherited reused_operand_sha256 is historical metadata; new module is independently tested, not covered by the old hash.')
 preferred=next(n for n in ('dual_boundary_slots','dual_boundary_uart','dual_boundary_side') if rows[n]['timing_status']=='PASS')
 # Functional preflight only: its complete empty-slot successor is implemented.
 preflight=ROOT/'simulation/results/load_bp_dual_boundary_preload'
 for p in preflight.rglob('*'):
  if not p.is_file() or 'obj' in p.parts or p.suffix in ('.vvp','.o','.exe','.pyc'):continue
  if p.name=='result.json':assert read(p)['status']=='PASS';verify(read(p),'preload preflight')
  copy(p,DEST/'preflight_operand_preload'/p.relative_to(preflight))
 snapshots={}
 with zipfile.ZipFile(DEST/'routed_snapshots.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
  for n in NAMES:
   for f in ('top_pnr.adf','top_pnr.netlist'):
    p=ROOT/f'simulation/results/load_bp_{n}/pds/place_route/{f}';key=n+'/'+f;z.write(p,key);snapshots[key]=sha(p)
 with zipfile.ZipFile(DEST/'routed_snapshots.zip') as z:
  for n,h in snapshots.items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 save(DEST/'routed_content_sha256.json',snapshots)
 for p in (ROOT/'tools').glob('*dual_timing80*.py'):copy(p,DEST/'tools'/p.name)
 for n in ('accept_dual_boundary_launch.py','check_dual_pair_annul.py','parse_dual_joint_timing.py','research_dual_ram_pds.py'):copy(ROOT/'tools'/n,DEST/'tools'/n)
 for p in (ROOT/'docs/dual_boundary_adoption').glob('*.json'):copy(p,DEST/'adoption'/p.name)
 copy(accepted,DEST/'accepted_dual_baseline.json')
 repro=ROOT/'simulation/results/dual_timing80_repro/result.json';assert read(repro)['status']=='PASS';copy(repro,DEST/'reproduction.json')
 final_repro=ROOT/'simulation/results/dual_timing80_repro/final_result.json';assert read(final_repro)['status']=='PASS';copy(final_repro,DEST/'final_reproduction.json')
 copy(ROOT/'tools/clean_dual_timing80_sim_cache.ps1',DEST/'tools/clean_dual_timing80_sim_cache.ps1')
 cleanup=ROOT/'simulation/cleanup_dual_timing80_result.json';copy(cleanup,DEST/'cleanup.json')
 cleanup2=ROOT/'simulation/cleanup_dual_timing80_slots_result.json';copy(cleanup2,DEST/'cleanup_slots.json')
 copy(ROOT/'tools/clean_dual_timing80_slots_sim_cache.ps1',DEST/'tools/clean_dual_timing80_slots_sim_cache.ps1')
 comparison=dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',accepted_variant=a['variant'],accepted_descriptor_sha256=sha(accepted),preferred_candidate=preferred,target_mhz=80,prior_archives_verified=prior,candidates=rows,limits=['One PDS implementation per distinct source/configuration, same device/options/board constraints and fixed images; genuine vendor PLL80, no seed sweep or timing exceptions.', 'Fixed 1/10 images retain CPU_HZ=75MHz metadata for cycle equivalence. Printed seconds/iterations per second are not physical measurements at80; cycle IPC is independently checked. Hardware UART80 is tested separately on parameterized physical top.', 'No new pipeline cycle, no new raw load-return forwarding and no new combinational MEM-ready-to-EX credit chain. Existing operand-forward/EX/MEM and load-launch control cones remain measured, not universally declared short.', 'Side specialization ties secondary JAL/JALR controls to zero. SAT proves admitted types never assert these controls. Pair-primary annul shortcut is formally equivalent but physical timing regresses; excluded from recommended source.', 'No board/Flash/game deployment or bitstream validation. Fmax is routed estimate, and passing80 timing is distinct from board stability.'])
 save(DEST/'comparison.json',comparison);write_report(comparison,a)
 save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
 for n,h in read(DEST/'manifest.json').items():assert sha(DEST/n)==h,n
 print('FROZEN',preferred,'files',len(read(DEST/'manifest.json')))
def write_report(x,a):
 rows=x['candidates'];best=rows[x['preferred_candidate']];r=best['resources'];p=best['global_paths'][0]
 lines=['# 双发核心80 MHz时序优化','','2026-10-21。上一轮 `dual_boundary_launch` 已按本次用户指令采纳；本轮为其上的隔离时序试验，尚未自动替换采纳描述。原单发工程、历史归档和固定镜像均保留。', '',f'推荐 `{x["preferred_candidate"]}`：80 MHz（12.500 ns）真实生成时钟约束下多角setup/hold全部通过，估算Fmax {best["estimated_fmax_mhz"]:.3f} MHz。固定10次窗口仍为2,807,614拍、退休2,808,261条、IPC **1.000230**，全部CRC/独立统计一致；未增加等待拍。','', '| 版本 | 约束MHz | Fmax MHz | slow setup ns | 最差hold ns | LUT | FF | 分布RAM | DRM/APM |','|---|---:|---:|---:|---:|---:|---:|---:|---|', f'| 已采纳launch | 75 | {a["estimated_fmax_mhz"]:.3f} | +0.473 | +0.106 | 11498 | 4495 | 709 | 48 / 4 |']
 labels={'dual_boundary_clock':'只改PLL的对照','dual_boundary_side':'副槽跳转控制裁剪','dual_boundary_pair':'配对取消窄化＋UART80（不取）','dual_boundary_uart':'仅整合UART80（不取）','dual_boundary_slots':'完整空槽预写＋UART80'}
 for n,v in rows.items():
  rr=v['resources'];hold=min(z['worst_slack_ns'] for k,z in v['corners'].items() if k.startswith('Hold'))
  lines +=[f'| {labels[n]} | 80 | {v["estimated_fmax_mhz"]:.3f} | {v["corners"]["Setup Summary(Slow Corner)"]["worst_slack_ns"]:+.3f} | {hold:+.3f} | {rr["LUT"]} | {rr["FF"]} | {rr["Distributed RAM"]} | {rr["DRM"]} / {rr["APM"]} |']
 lines +=['',f'推荐版相对已采纳版：LUT {r["LUT"]-11498:+d}、FF {r["FF"]-4495:+d}；分布RAM/DRM/APM不变。原片上50 MHz输入仍是20.000 ns，未改板级输入约束；独立复制并由紫光IP工具生成PLL，50/5×64/8=80 MHz。没有false/multicycle path、降uncertainty或换seed。', '', '首先将副槽不可能使用的JAL/JALR控制置零；该副槽仍支持原有ALU、条件分支及共享乘法，主槽JAL/JALR不变。删掉了副槽旁路操作数经过间接地址加法、目标比较再到分支控制的无效组合路径。两位不再使用的控制在双槽ID/EX存储中被综合裁掉，副槽裁剪初版因此比launch少4个FF；空槽重构后的最终资源以表中实报为准。','', '另外试过将主槽导致副槽取消的条件改为更窄的配对专用判定。SAT证明等价，但完整物理结果77.083 MHz、slow setup −0.473 ns，5个违例；最差路径转移到f_valid→操作数选择→副槽结果→MEM，主要是9.408 ns布线。这项不因逻辑更少而强行保留，推荐源码没有采用它。','', '80 MHz物理顶层通过CLOCK_HZ参数传到UART，实际DIV=694；实RTL仿真逐拍验证0xA5完整8N1帧。测试PLL使用时钟替身，实际PLL12.500 ns周期另由PDS生成时钟报告确认。比较用SoC默认仍为75 MHz，以完整保留原镜像及测试口径。','', '各角结果：','', '| 角 | slack ns | 违例端点 |','|---|---:|---:|']
 for n,v in best['corners'].items():lines +=[f'| {n} | {v["worst_slack_ns"]:+.3f} | {v["failing_endpoints"]} |']
 lines +=['','UART80直接整合版只差0.084 ns，但仍有2个setup违例，未当作达标。其最差路径为完整非法指令译码→issue→操作数FF的CE，CE setup要求0.747 ns，布线8.831 ns。后续空槽预写版将未占用物理槽的数据及元数据按寄存的count/rd提前采样；入槽动作只在实际push时更新占用数、写指针及新指令的等待状态；pop和旁路捕获规则不变。空槽的token/dep等无效元数据也允许提前采样，在push前不会作为有效指令使用。已占用槽仍只按原旁路规则捕获值。由此移除晚到issue对宽数据/元数据CE的控制，未放宽非法指令串行化、异常精确性或配对规则。','', '空槽采样增加无效数据的切换活动；没有新增流水级、队列深度或有效指令等待拍，未测功耗。先做仅操作数预写的功能预检，再扩展到完整空槽；完整空槽版重新完成300000拍独立队列等价检查（600000次边沿检查），并通过整核检查和固定1/10次镜像，不以旧模块hash复用替代新逻辑验证。']
 if best.get('selected_paths'):
  lines +=['','定向路径查询（从同一路由快照只读分析）：','','| 终点类别 | setup slack ns | 逻辑级数 | 逻辑/布线 ns |','|---|---:|---:|---|']
  for n,v in best['selected_paths'].items():
   q=v[0];lines +=[f'| {n} | {q["slack_ns"]:+.3f} | {q["logic_levels"]} | {q["logic_ns"]:.3f} / {q["route_ns"]:.3f} |']
 lines +=['',f'当前最差路径：`{p["start"]}` → `{p["end"]}`；{p["logic_levels"]}级逻辑，逻辑{p["logic_ns"]:.3f} ns、布线{p["route_ns"]:.3f} ns，路径内最大数据扇出{p["max_data_fanout"]}。', '', '这次没有增加跨模块控制链，也没有把旁路再寄存一拍。原有旁路→EX→MEM数据/控制路径和EX本地load启动路径仍存在，不能说已经全部切断；80 MHz余量以表内实际数值为准。五源旁路来源和优先级、FIFO深度、双发准入及访存返回级数不变；ID/EX空槽存储写入方式已按上文重构。','', '验证包括63项架构/随机差分/ISA检查、7项前端和寄存器堆/双发故障统计、6项分支乘法配对、4项取消、8项真实未来tag协议、4项乘法tag协议、4项逐拍load检查、4项MEM协议、10项地址发布检查和危险lint/SAT准入检查。副槽裁剪初版复用精确hash对应的操作数证据；空槽预写版重新执行3×100000拍独立等价检查，整核、1/10镜像、实顶层UART均另行通过。每份物理候选只跑一次PDS。','', '完整机器数据见 `dual_timing80/comparison.json`；RTL、工具、仿真证据、STA、失败试验和压缩路由快照见同目录清单。编译obj缓存已单独记录清理，RTL/镜像/日志/报告保留。','', '尚未上板。固定镜像中的75 MHz打印参数未改，因此打印的秒数不是80 MHz实测；本轮使用独立周期计数计算IPC。80 MHz相对75 MHz的同IPC理论吞吐提升6.667%，不能当成已测量的板上成绩。']
 report=ROOT/'docs/dual_timing80.md';report.write_text('\n'.join(lines)+'\n',encoding='utf-8');copy(report,DEST/'report.md')
 p=ROOT/'README.md';s=p.read_text(encoding='utf-8');s+=f'\n80 MHz时序试验完成：推荐 `{x["preferred_candidate"]}`，详见 [统一报告](docs/dual_timing80.md)。本轮尚未采纳；当前已采纳双发开发基线仍为 `dual_boundary_launch`。\n';p.write_text(s,encoding='utf-8')
if __name__=='__main__':main()
