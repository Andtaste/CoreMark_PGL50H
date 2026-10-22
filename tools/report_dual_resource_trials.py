"""Freeze resource experiments and report measured tradeoffs; do not adopt."""
from pathlib import Path
import hashlib,json,re,shutil,zipfile
from parse_dual_joint_timing import paths
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'docs/dual_resource_trials'
TRIALS=('resourceside','resourcequeue','resourceboth','resourcecompare')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def dram(p):
 s=p.read_text();d={}
 for m in re.finditer(r'(?ms)^module (\w+).*?^endmodule',s):
  n=len(re.findall(r'GTP_RAM(?:16|32)X1(?:DP|SP) /\*',m[0]))
  if n:d[m[1]]=n
 return d
def main():
 assert not (DEST/'manifest.json').exists()
 descriptor=ROOT/'docs/accepted_dual_baseline.json';a=read(descriptor);guard=sha(descriptor);assert a['variant']=='dual_boundary_next_pairbranch'
 for key in ('source_sha256','ip_sha256','evidence_sha256'):
  for n,h in a[key].items():assert sha(ROOT/n)==h,(key,n)
 reproduction=ROOT/'simulation/results/dual_resource_reproduction';assert read(reproduction/'result.json')['status']=='PASS'
 rows={};verified={}
 def verify(x,label):
  for k in ('input_sha256','actual_compile_sha256','ip_sha256'):
   for n,h in x.get(k,{}).items():
    p=ROOT/n
    if not p.exists() and n.replace('\\','/').startswith('tmp/'):p=ROOT.parent/n
    assert p.is_file() and sha(p)==h,(label,k,n)
    verified[n]=h
    if not n.replace('\\','/').startswith('simulation/results/load_bp_dual_boundary_next_') and p.suffix!='.adf':copy(p,DEST/'inputs'/n)
 for t in TRIALS:
  src=ROOT/('simulation/results/load_bp_dual_boundary_next_'+t);g=read(src/'generation.json');assert g['accepted_dual_sha256']==guard
  generator=reproduction/'generate_pc_v1.py' if t!='resourcecompare' else ROOT/'tools/generate_dual_resource_trials.py';assert sha(generator)==g['generator_sha256']
  for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
  verify(g,t+' generation');pd=read(src/'pds/result.json');assert pd['status'] in ('PASS','TIMING_FAILED') and pd['pds_exit_code']==0
  assert sha(src/'pds/run.tcl')==pd['tcl_sha256']
  perf=read(src/'performance/result.json');assert perf['status']=='PASS'
  assert int(perf['metrics']['Stats window cycles'])==a['coremark_stats_cycles'] and int(perf['metrics']['Retired instructions'])==a['retired'] and perf['dual']==a['dual']
  expected={'checks':63,'pair_checks':6,'cancel_checks':4,'audit_checks':4,'protocol':8,'mul_protocol':4,'posted_soc_final':6,'uart80':1,'timeline_checks':4}
  for sub,count in expected.items():
   x=read(src/sub/'result.json');assert x['status']=='PASS' and len(x['tests'])==count,(t,sub)
  suite='resource_suite' if t in ('resourcequeue','resourceboth') else 'next_suite';assert read(src/suite/'result.json')['status']=='PASS'
  if t!='resourcecompare':assert read(src/'next_directed/result.json')['status']=='PASS'
  if t in ('resourcequeue','resourceboth','resourcecompare'):assert read(src/'resource_proof/result.json')['status']=='PASS'
  if t=='resourceboth':assert read(src/'resource_lockstep/result.json')['status']=='PASS'
  for p in src.rglob('result.json'):
   if any(k in p.parts for k in ('obj','compile','rtr.db')):continue
   x=read(p);verify(x,str(p))
   if p.parent.name=='next_suite' and t in ('resourcequeue','resourceboth'):
    assert x['status']=='FAILED' # Literal legacy width audit; original record retained.
   else:assert x['status'] in ('PASS','TIMING_FAILED'),p
  rows[t]=dict(timing=pd,cycles=int(perf['metrics']['Stats window cycles']),retired=int(perf['metrics']['Retired instructions']),ipc=a['ipc'],dual=perf['dual'],critical_path=paths(src/'pds/report_timing/top.rtr')[0],distributed_ram_modules=dram(src/'pds/synthesize/top_syn.vm'),functional_suite=suite,all_corners_pass=all(c['worst_slack_ns']>=0 and c['failing_endpoints']==0 for c in pd['corners'].values()))
  for p in src.rglob('*'):
   if not p.is_file():continue
   rel=p.relative_to(src)
   if any(k in rel.parts for k in ('obj','compile','rtr.db')) or p.suffix in ('.vvp','.o','.exe','.pyc','.elf','.bin'):continue
   if rel.parts[0]=='pds' and rel.as_posix() not in ('pds/result.json','pds/run.tcl','pds/build.log','pds/report_timing/top.rtr','pds/device_map/top.dmr','pds/place_route/top.prr','pds/synthesize/top.snr','pds/synthesize/apm_drm_lutram_utilization.log'):continue
   if rel.parts[0]=='next_paths' and len(rel.parts)>2:continue
   copy(p,DEST/t/rel)
  z=DEST/t/'routed_snapshot.zip'
  with zipfile.ZipFile(z,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as ar:
   for p in (src/'pds/place_route/top_pnr.adf',src/'pds/synthesize/top_syn.vm'):ar.write(p,p.relative_to(src).as_posix())
  with zipfile.ZipFile(z) as ar:
   for n in ar.namelist():assert hashlib.sha256(ar.read(n)).hexdigest()==sha(src/n),n
 for p in reproduction.rglob('*'):
  if p.is_file():copy(p,DEST/'reproduction'/p.relative_to(reproduction))
 for p in (ROOT/'tools').glob('*resource*'):
  if p.is_file():copy(p,DEST/'tools'/p.name)
 copy(descriptor,DEST/'accepted_baseline_snapshot.json')
 baseline_modules=dram(ROOT/a['source_directory']/'pds/synthesize/top_syn.vm');assert sum(baseline_modules.values())==709
 labels=dict(resourceside='副槽 PC 重建',resourcequeue='EX/MEM 队列 PC 压缩',resourceboth='两种压缩合并',resourcecompare='有符号/无符号比较共享')
 eligible=[t for t,r in rows.items() if r['all_corners_pass'] and r['timing']['resources']['LUT']<a['resources']['LUT'] and r['timing']['resources']['FF']<=a['resources']['FF']]
 preferred=min(eligible,key=lambda t:rows[t]['timing']['resources']['LUT']) if eligible else None
 save(DEST/'comparison.json',dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',preferred_candidate=preferred,accepted_descriptor_sha256=guard,accepted=a,candidates=rows,baseline_distributed_ram_modules=baseline_modules))
 lines=['# 采纳记录与资源优化试验','', '**上一轮推荐的 `dual_boundary_next_pairbranch` 已采纳；本轮资源候选均保持隔离，未自动替换基线。**','',f'当前基线：80 MHz，估算 Fmax {a["estimated_fmax_mhz"]:.3f} MHz，固定 10 次诊断窗口 {a["coremark_stats_cycles"]:,} 拍 / {a["retired"]:,} 条，IPC {a["ipc"]:.8f}。副槽退休 {a["dual"]["secondary_retired"]:,}。采纳详情见 [独立记录](dual_pairbranch_adoption/adoption.json)。','', '| 版本 | LUT | FF | 分布 RAM | DRM/APM | Fmax MHz | 慢角 setup ns | 最差 hold ns | 80 MHz |','|---|---:|---:|---:|---|---:|---:|---:|---|']
 def row(label,pd):
  r=pd['resources'];c=pd['corners'];hold=min(v['worst_slack_ns'] for k,v in c.items() if k.startswith('Hold'))
  return f'| {label} | {r["LUT"]} | {r["FF"]} | {r["Distributed RAM"]} | {r["DRM"]}/{r["APM"]} | {pd["estimated_fmax_mhz"]:.3f} | {c["Setup Summary(Slow Corner)"]["worst_slack_ns"]:+.3f} | {hold:+.3f} | '+('通过' if all(v['worst_slack_ns']>=0 and v['failing_endpoints']==0 for v in c.values()) else '不通过')+' |'
 lines.append(row('已采纳 pairbranch',a))
 for t,r in rows.items():lines.append(row(labels[t],r['timing']))
 lines+=['', ('建议后续采纳隔离候选 `dual_boundary_next_'+preferred+'`。' if preferred else '本轮不建议合入资源候选，保留刚采纳的 pairbranch 基线。'),'', '四版均与基线具有完全相同的固定 10 次周期、退休数、双发发射/退休数；没有通过增加等待、减少 FIFO 深度、缩小 BTB 或删减 ISA 换资源。Fmax 是布局布线 STA 估算，实际 PLL 仍为 80 MHz。','', '## 资源去向与冗余核查','', '以最终综合网表实际原语实例计数：寄存器堆 256、EX/MEM FIFO 215、BTB 两个 bank 共 174、取指 FIFO 64，合计 **709 个分布 RAM**。前期映射日志仍列 FIFO 240、BTB 178，那是后续剪枝前的数值，不应直接相加作为最终占用。分布 RAM 属于 LUT 资源，不额外消耗 48 个 DRM；DRM 和 4 个 APM 本轮均未增加。','', '寄存器堆为四读两写，两个单写 bank 各复制四份以供读端口。直接减少副本会改变端口能力或引入冲突等待，不能当作无损冗余删除。`inflight` 调试计数、未读取的 payload 操作数字段和其他未用信号已经被综合裁剪；仅删 RTL 名字没有实物收益。','', '副槽 PC 总等于主槽 PC+4，因此可以省两个队列槽中的重复 PC。原本低两位已经被综合成常量，实际减少 60 个 FF。EX/MEM 的分支 next-PC 与辅助字重复；将 FIFO 249 位压到 217 位，分支故障时用独立保存的 PC/指令恢复故障辅助字，其余 next-PC 从 PC+4 恢复。逻辑上少 32 位，最终 RAM 实际少 30 个；恢复和复用逻辑可能使总 LUT 上升，不能只看 RAM 减少。','', '比较共享版将 signed less 改为“符号不同取 A 的符号，否则使用 unsigned less”，ALU 与分支分别共享各自的比较结果。源操作数、旁路、队列、控制寄存边界均不变。','', '## 时序与长链','']
 for t,r in rows.items():
  p=r['critical_path'];lines +=[f'- **{labels[t]}**：`{p["start"]}` → `{p["end"]}`；{p["logic_levels"]} 级，逻辑 {p["logic_ns"]:.3f} ns / 布线 {p["route_ns"]:.3f} ns，路径最大数据扇出 {p["max_data_fanout"]}。']
 lines+=['', '未增加 RAM 返回旁路、ready 的跨级组合反馈或新的成组等待网络。PC 重建增加的是现有寄存边界间的数据计算；已存在的旁路到访存/控制路径仍须以完整 STA 判定。省下存储也会改变逻辑映射和布局，面积更小不代表时序更好；本轮严格按相同 12.500 ns、多角 setup/hold 和原布线选项比较，没有换种子搜索。','', '## 验证与复现','', '四版均完成 63 项 ISA/随机/SoC 回归、固定 1/10 次 CoreMark、配对 6 项、取消 4 项、危险 lint 与准入证明、旁路协议 8 项、流水乘法协议 4 项、posted-store 实际 SoC 6 项、UART80 和逐拍时序 4 项。三版 PC 压缩另跑访存+副槽分支及异常取消 6 项；合并版还与采纳基线进行 10 项同输入逐拍对照，检查请求、完整 EX/MEM 包和退休轨迹。','', '队列两版：抽取实际编码/恢复 RTL，以任意包、控制、预测和错误位证明 280 位 MEM 包完全等价，覆盖地址回绕及非法/取指错误。比较共享版：实际完整 EX 输出和控制输出的全输入 SAT 等价。形式证明中两边 DIV 结果均关闭；DIV RTL 未改，独立 ISA 回归仍覆盖除法。','', '旧静态审计写死 FIFO WIDTH(249)，因此两个 217 位候选首次审计失败；原失败记录保留。后续仅把宽度断言适配为 217，并先强制要求编码等价证明通过，其余 lint、准入证明、深度及注册 credit 检查保留。最终验证状态见各候选 `resource_suite/result.json`。','', '生成器 v1 的原字节按 SHA 归档，四版 RTL/IP 均在独立目录重新生成并逐文件验证。历史 runner 的部分 scope 文案仍写 storewrite，实际父版本以 `generation.json.accepted_dual_sha256` 和本次采纳快照为准。','', '未上板，未测试游戏工作负载；此处是固定镜像诊断比较，不是正式 CoreMark 分数。旧试验归档和原单发工程保留。','']
 report=ROOT/'docs/dual_resource_trials.md';report.write_text('\n'.join(lines),encoding='utf-8');copy(report,DEST/'report.md')
 save(DEST/'archive_verification.json',dict(status='PASS',accepted_descriptor_sha256=guard,verified_input_files=len(verified),candidate_count=4,all_new_resource_candidates_unadopted=True))
 assert sha(descriptor)==guard
 save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
 for n,h in read(DEST/'manifest.json').items():assert sha(DEST/n)==h,n
 print('FROZEN resource trials',len(read(DEST/'manifest.json')),'files; preferred',preferred)
if __name__=='__main__':main()
