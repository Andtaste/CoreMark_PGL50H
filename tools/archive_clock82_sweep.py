"""Freeze every seed, input and timing failure; never confuse PnR exit with timing pass."""
from pathlib import Path
import hashlib,json,re,shutil,zipfile,csv
from collect_clock82_seeds import parse,routed_resources
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/clock82_multiseed_20261022'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def main():
 assert not (OUT/'manifest.json').exists();s=read(OUT/'seed_results.json');prep=read(OUT/'prepared.json');assert s['status']=='COMPLETE'
 checks=ROOT/'simulation/results/clock82_checks';assert read(checks/'result.json')['status']=='PASS' and read(OUT/'source_equivalence.json')['status']=='PASS'
 for n,h in prep['input_sha256'].items():assert sha(ROOT/n)==h,n
 extra=OUT/'extension_plan.json'
 if extra.exists():
  x=read(extra);assert sha(ROOT/x['mapped_input_db'])==x['mapped_db_sha256'];assert sha(ROOT/x['trial_directory']/'more_seeds.tcl')==x['tcl_sha256']
 route=read(OUT/'route_results.json') if (OUT/'route_results.json').exists() else dict(status='COMPLETE',completed=0,routes={},passing=[])
 assert route['status']=='COMPLETE'
 if (OUT/'route_plan.json').exists():
  rp=read(OUT/'route_plan.json');assert sha(ROOT/rp['placement_db'])==rp['placement_sha256'];assert sha(ROOT/rp['trial_directory']/'route_seeds.tcl')==rp['tcl_sha256']
 for kind in ('place','route'):
  path=OUT/f'additional_{kind}_plans.json'
  for plan in read(path) if path.exists() else []:
   field='mapped_input_db' if kind=='place' else 'placement_db';hf='mapped_db_sha256' if kind=='place' else 'placement_sha256'
   assert sha(ROOT/plan[field])==plan[hf]
   assert sha(ROOT/plan['trial_directory']/'search.tcl')==plan['tcl_sha256']
 all_records=dict(s['seeds']);all_records.update({f"p{x['gplace_seed']}_r{x['groute_seed']}":x for x in route['routes'].values()})
 verify={}
 for p in checks.glob('*result.json'):
  x=read(p);assert x['status']=='PASS'
  for n,h in x.get('input_sha256',{}).items():assert sha(ROOT/n)==h,n;verify[n]=h
 for seed,x in all_records.items():
  folder=ROOT/x['directory'];assert sha(folder/'top.rtr')==x['sta_sha256'] and sha(folder/'top_pnr.adf')==x['routed_sha256']
  assert parse(folder/'top.rtr')['status']==x['status']
  dest=OUT/'seeds'/seed
  for name in ('top.rtr','top.prr','run.log','clock_utilization.txt','top_timing_summary_after_hold_fix.txt'):
   if (folder/name).exists():copy(folder/name,dest/name)
  for p in folder.rglob('*'):
   if p.is_file() and (p.suffix=='.rcf' or (len(p.relative_to(folder).parts)>1 and p.suffix in ('.rtr','.prr','.log'))):copy(p,dest/p.relative_to(folder))
  z=dest/'routed_snapshot.zip'
  with zipfile.ZipFile(z,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as ar:
   ar.write(folder/'top_pnr.adf','top_pnr.adf')
   if (folder/'top_plc.adf').exists():ar.write(folder/'top_plc.adf','top_plc.adf')
  with zipfile.ZipFile(z) as ar:assert hashlib.sha256(ar.read('top_pnr.adf')).hexdigest()==x['routed_sha256']
 # Verify dispatcher CSV and native final STA agree for every seed.
 folders=['pds82_seed_sweep','pds82_seed_sweep_more','pds82_route_sweep']
 for kind in ('place','route'):
  path=OUT/f'additional_{kind}_plans.json'
  folders += [Path(plan['trial_directory']).name for plan in read(path)] if path.exists() else []
 for name in folders:
  folder=ROOT/'hardware'/name
  if not folder.exists():continue
  table=folder/'place_route/multiseed_result.csv';rows=list(csv.DictReader(table.read_text().splitlines()))
  native_records={str(x['groute_seed']) if 'groute_seed' in x else k:x for k,x in all_records.items() if Path(x['directory']).parts[-3]==name}
  seen=set()
  for row in rows:
   k=row['Seed']
   if not k or not k.isdigit():continue
   assert k in native_records and row['State']=='OK',row
   seen.add(k)
   for col,group in (('Setup(Slow)','Setup Summary(Slow Corner)'),('Setup(Fast)','Setup Summary(Fast Corner)'),('Hold(Slow)','Hold Summary(Slow Corner)'),('Hold(Fast)','Hold Summary(Fast Corner)')):assert abs(float(row[col])-native_records[k]['corners'][group]['worst_slack_ns'])<0.0001,(k,col)
  assert seen==set(native_records),(name,seen,set(native_records))
  for p in folder.rglob('*'):
   if not p.is_file():continue
   rel=p.relative_to(folder)
   keep=rel.parts[0] in ('source','ipcore','constraints','memory') and p.suffix in ('.v','.idf','.fdc','.hex')
   keep|=len(rel.parts)==1 and p.suffix in ('.tcl','.pds','.csv','.log')
   keep|=rel.as_posix() in ('synthesize/top.snr','synthesize/top_syn.vm','device_map/top.dmr','device_map/top_map.adf','place_route/multiseed_result.csv','report_timing/top.rtr')
   if keep:copy(p,OUT/'trials'/name/rel)
 for p in checks.iterdir():
  if p.is_file() and p.suffix in ('.json','.v','.log','.uart'):copy(p,OUT/'checks'/p.name)
 guard_check=ROOT/'simulation/results/clock82_guard_checks/result.json';assert read(guard_check)['status']=='PASS'
 for n,h in read(guard_check)['input_sha256'].items():assert sha(ROOT/n)==h,n
 copy(guard_check,OUT/'checks/checkpoint_guard_result.json')
 repeat=read(OUT/'reproduction_plan.json');folder=ROOT/repeat['trial_directory'];assert sha(ROOT/repeat['mapped_input_db'])==repeat['mapped_db_sha256'];assert parse(folder/'report_timing/top.rtr')['status']=='PASS'
 for n in ('reproduce.tcl','reproduce.log','place_route/top.prr','report_timing/top.rtr'):
  copy(folder/n,OUT/'reproduction'/n)
 with zipfile.ZipFile(OUT/'reproduction/native_snapshot.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as ar:
  for n in ('clock82_map.adf','place_route/top_pnr.adf'):ar.write(folder/n,n)
 # Existing 80MHz GUI runs are pre-existing evidence, never counted as82 passes.
 selection=read(OUT/'selected_config.json') if (OUT/'selected_config.json').exists() else dict(chosen=None,passing_cases=[])
 active=ROOT/'hardware/pds';promoted=selection['chosen'] is not None
 if promoted:
  assert read(OUT/'main_result.json')['status']=='PASS' and parse(active/'report_timing/top.rtr')['status']=='PASS'
  current_hz=82000000
 else:
  assert sha(ROOT/'docs/accepted_dual_baseline.json')==prep['accepted_descriptor_sha256'];assert 'CLOCK_HZ(80000000)' in (active/'source/source/top.v').read_text();current_hz=80000000
  for n,h in prep['before80_source_sha256'].items():
   if n.replace('\\','/').startswith(('source/','ipcore/','constraints/','memory/')):assert sha(active/n)==h,n
 closest=max(all_records,key=lambda k:all_records[k]['corners']['Setup Summary(Slow Corner)']['worst_slack_ns']);best=selection['chosen'] if promoted else all_records[closest]
 perf=read(checks/'performance_result.json');m=perf['metrics'];cycles=int(m['Stats window cycles']);retired=int(m['Retired instructions']);ticks=int(m['Benchmark cycles64']);iterations=int(m['Iterations'])
 resources={'LUT':11013,'FF':4476,'Distributed RAM':709,'DRM':48,'APM':4}
 native_iterations=sum(max(1,len(list((ROOT/x['directory']).glob('route_constraint_ite_*/top.rtr')))) for x in all_records.values())
 placed=read(OUT/'main_result.json')['routed_resources'] if promoted else best['routed_resources']
 if promoted:
  for p in active.rglob('*'):
   if not p.is_file():continue
   rel=p.relative_to(active)
   keep=rel.parts[0] in ('source','ipcore','constraints','memory') and p.suffix in ('.v','.idf','.fdc','.hex')
   keep|=rel.parts[0]=='checkpoints'
   keep|=rel.as_posix() in ('new_core.tcl','new_core.pds','rebuild_from_rtl.tcl','BASELINE.json','device_map/top.dmr','place_route/top.prr','report_timing/top.rtr','synthesize/top_syn.vm','clock82_main_build.log','clock82_pinned_build.log')
   if keep:copy(p,OUT/'main'/rel)
  with zipfile.ZipFile(OUT/'main/routed_snapshot.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as ar:
   for name in ('place_route/top_pnr.adf','device_map/top_map.adf'):
    ar.write(active/name,name)
 summary=dict(status='CLOCK82_VERIFIED_AND_PROMOTED' if promoted else 'CLOCK82_TIMING_FAILED_MAIN80_RETAINED',trial_count=len(all_records),placement_trials=s['completed'],fixed_placement_route_trials=route['completed'],passing_cases=selection['passing_cases'],selected_config=selection['chosen'],closest_case=closest,closest_setup_ns=all_records[closest]['corners']['Setup Summary(Slow Corner)']['worst_slack_ns'],configured_main_hz=current_hz,trial_hz=82000000,resources=resources,ipc=retired/cycles,cycles=cycles,retired=retired,coremark_per_mhz=iterations*1000000/ticks,clock82_diagnostic_projection=iterations*82000000/ticks,seed_results=s,route_results=route,verified_test_input_files=len(verify),scope='Real PLL82 and UART712; CPU RTL unchanged. All native final per-seed summaries compared against dispatcher CSV. Projection is not a board result or a valid long-duration CoreMark score.')
 save(OUT/'result.json',summary)
 summary.update(native_pnr_runs_including_priority_iterations=native_iterations,routed_resources=placed,resource_basis='resources: mapping; routed_resources: final physical resource counts')
 save(OUT/'result.json',summary)
 lines=['# 82 MHz 多 seed 布局验证','',('**82 MHz 已全角收敛，并已同步主工程。**' if promoted else '**本轮 82 MHz 尚未收敛；主工程和采纳记录保留已验证的 80 MHz。**'),'',f'共完成 **{s["completed"]} 个实际 82 MHz 布局 seed**（0～{s["completed"]-1}），通过 {len(s["passing"])} 个。CPU 五级流水、配对准入、旁路和队列深度均未改写；全部17个RTL仅顶层 CLOCK_HZ 从80000000变为82000000。','', 'PLL 由紫光 IP 工具重新生成，50/5×82/10=82 MHz，VCO820 MHz；UART 实际分频712并通过0xA5完整8N1逐拍检查。PDS生成时钟显示12.195ns /82.001MHz是报告三位小数取整，硬件比值为82MHz。50MHz板级输入保持20ns，未加false/multicycle path或放松时序约束。','', '| Seed | 慢角setup ns | 快角setup ns | 慢角hold ns | 快角hold ns | 估算Fmax MHz | 全角通过 |','|---:|---:|---:|---:|---:|---:|---|']
 for k,x in sorted(s['seeds'].items(),key=lambda z:int(z[0])):
  c=x['corners'];v=[c[g]['worst_slack_ns'] for g in ('Setup Summary(Slow Corner)','Setup Summary(Fast Corner)','Hold Summary(Slow Corner)','Hold Summary(Fast Corner)')]
  lines.append(f'| {k} | {v[0]:+.3f} | {v[1]:+.3f} | {v[2]:+.3f} | {v[3]:+.3f} | {x["estimated_fmax_mhz"]:.3f} | '+('通过' if x['status']=='PASS' else '未通过')+' |')
 for k,x in sorted(route['routes'].items(),key=lambda z:(z[1]['gplace_seed'],z[1]['groute_seed'])):
  c=x['corners'];v=[c[g]['worst_slack_ns'] for g in ('Setup Summary(Slow Corner)','Setup Summary(Fast Corner)','Hold Summary(Slow Corner)','Hold Summary(Fast Corner)')]
  lines.append(f'| 固定P{x["gplace_seed"]}/R{x["groute_seed"]} | {v[0]:+.3f} | {v[1]:+.3f} | {v[2]:+.3f} | {v[3]:+.3f} | {x["estimated_fmax_mhz"]:.3f} | '+('通过' if x['status']=='PASS' else '未通过')+' |')
 lines.insert(5,f'另对最接近的布局固定位置，完成 **{route["completed"]} 个路由seed**，合计 **{len(all_records)} 次实现**；固定布局路由从同一 top_plc.adf 开始，SHA已核对。')
 lines.insert(6,f'上述为独立seed配置数；关键路径优先布线含多轮迭代，按每轮最终STA累计实际完成 **{native_iterations} 次PNR**。优先布线仅调整网络布线顺序；performance模式以运行时间换时序质量，均未改CPU逻辑或时序例外。')
 lines+=['',f'最佳接近结果为 **{closest}**：慢角 setup **{all_records[closest]["corners"]["Setup Summary(Slow Corner)"]["worst_slack_ns"]:+.3f} ns**。'+('最终主工程独立重建结果见 main_result.json。' if promoted else '负 slack 即违例；工具进程成功完成、CSV State=OK 或 UserFilter=1 均不等于时序通过。'),'', f'初始10个seed都未通过，继续扩展至{s["completed"]}个布局seed和{route["completed"]}个固定布局路由seed。扩展轮直接复用同一个 top_map.adf 或指定 top_plc.adf，SHA已校验；没有重新综合或改变输入设计、PLL、约束。并行度见各计划文件，同样的hold修复和控制链长度选项，所有原始失败均保留。','', '此前主工程已有用户运行的80MHz种子结果，seed8 slow setup+0.422ns、估算Fmax82.795MHz；这属于80MHz PLL/原UART配置，未当作本轮82MHz收敛证据。改变真实PLL、UART常量和综合时序目标会改变映射与布局，不能把原80MHz的正余量直接平移为82MHz已经通过。','', '## 功能、性能与资源','', f'CLOCK_HZ82实际SoC固定1/10次镜像CRC和独立计数核对均通过。10次统计窗口 **{cycles:,}拍 / {retired:,}条**，IPC **{retired/cycles:.8f}**；与80MHz版周期完全一致。','', '**11013 LUT /4476 FF /709分布RAM /48 DRM /4 APM**。相比80MHz版少27 LUT；这是时钟/UART常量与综合映射变化，不是新增CPU资源优化。未引入新跨级组合控制反馈；已有旁路选择到访存/控制的路径仍是频率限制来源。','',f'归一化诊断 **{iterations*1000000/ticks:.6f} CoreMark/MHz**；若在82MHz通过并稳定运行，对应约 **{iterations*82000000/ticks:.2f}**、相对80MHz吞吐+2.5%。'+('本轮已通过STA，尚未上板。' if promoted else '本轮时序未通过，因此此处82MHz分数只是换算，不能作为当前可用成绩。'),'', '固件仍保留75MHz打印元数据，日志的秒数和总分应按实际时钟换算；CRC PASS与短跑<10秒的Score status分开判断。未声称官方长跑成绩或板上稳定性。','', '## 最接近 seed 的实际路径','']
 for p in best['critical_paths']:
  lines.append(f'- `{p["start"]}` → `{p["end"]}`：{p["logic_levels"]}级，逻辑{p["logic_ns"]:.3f}ns /布线{p["route_ns"]:.3f}ns，slack{p["slack_ns"]:+.3f}ns。')
 lines+=['', '各seed使用最终top.rtr与最终dispatcher CSV，未拿placement或hold修复过程中的中间summary替代最终结果。现有未使用板级端口仍沿用原约束；没有为这轮增加例外。','', '原80MHz源码/IP/镜像/工程及路由结果保存在 before80_snapshot.zip，逐文件SHA见before80_manifest.json。每个82MHz seed的STA、日志及压缩路由快照均已保存。主工程当前频率以 result.json / docs/active_pds_baseline.json 为准。','']
 lines+=['',f'最终布线后资源（包含物理优化复制）为 **{placed["LUT"]} LUT / {placed["FF"]} FF / {placed["Distributed RAM"]} 分布RAM / {placed["DRM"]} DRM / {placed["APM"]} APM**。上文11013 LUT是映射阶段口径；此前80MHz seed8布线后为11066 LUT，其余资源相同。']
 lines+=['','## seed 与映射检查点的复现条件','', '重新综合可能交换寄存器文件128个等价RAM读副本的实例名，从而扰动同一seed的布局。主目录首次重新综合后的22/4结果为setup−0.977ns；这次失败的网表、映射、路由与日志完整保留在fresh_main_failed中。全25模块结构对比证明只有这些副本名发生一一置换，原语参数、连接信号和位号均等价。','', '独立目录从原82MHz固定映射重新执行完整布局22／路由4，准确复现setup+0.040ns与hold最小+0.117ns。随后主工程new_core.tcl默认重新编译、综合、映射，通过所有输入SHA与完整结构连线核对后装入原固定映射，再由PDS重新布局布线与最终STA，也再次得到上述全角正余量。主工程最终原始报告与固定映射在main/中。','', '构建入口使用hardware/pds/checkpoints/clock82_checkpoint.json和verify_clock82_checkpoint.py。源码、IP、镜像或FDC变化即拒绝装入旧检查点；编译网表的实际连接变化也拒绝。隔离项目负向测试已验证两类拒绝都不会覆盖映射。输入变化时请使用rebuild_from_rtl.tcl重新综合并重新寻找种子；PDS GUI直接重新综合也会产生新映射。完整复现本轮结果使用new_core.tcl。没有把一组seed宣传为脱离其映射输入仍可通用。','', '本轮CPU RTL仅顶层时钟常量变化，完整固定1/10次功能CRC与独立硬件计数一致。未增加CPU跨模块组合控制链。全角收敛属于PDS静态时序结果，尚未上板。']
 (OUT/'README.md').write_text('\n'.join(lines),encoding='utf-8')
 for p in (ROOT/'tools').glob('*clock82*'):
  if p.is_file():copy(p,OUT/'tools'/p.name)
 copy(ROOT/'simulation/results/clock82_seed_probe/help.log',OUT/'native_pnr_help.log')
 save(OUT/'archive_verification.json',dict(status='PASS',seed_count=len(all_records),passing=selection['passing_cases'],configured_main_hz=current_hz,all_seed_sta_matches_dispatcher_csv=True,all_native_route_snapshots_hash_verified=True,verified_input_files=len(verify)))
 save(OUT/'manifest.json',{str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='manifest.json'})
 for n,h in read(OUT/'manifest.json').items():assert sha(OUT/n)==h,n
 print('FROZEN',summary['status'],s['completed'],'seeds,',len(read(OUT/'manifest.json')),'files')
if __name__=='__main__':main()
