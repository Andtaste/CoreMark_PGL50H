"""Publish requested clock82 only after the active main-directory rebuild passes."""
from pathlib import Path
from datetime import datetime
import json,hashlib,re
from collect_clock82_seeds import parse,routed_resources
from compare_clock82_netlists import compare
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
 out=ROOT/'docs/clock82_multiseed_20261022';promotion=read(out/'promotion.json');seeds=read(out/'seed_results.json');checks=read(ROOT/'simulation/results/clock82_checks/result.json');main=ROOT/'hardware/pds';trial=ROOT/'hardware/pds82_seed_sweep'
 chosen=read(out/'selected_config.json')['chosen'] if (out/'selected_config.json').exists() else dict(gplace_seed=seeds['best_seed'],groute_seed=0)
 assert seeds['status']=='COMPLETE' and chosen['gplace_seed']==promotion['chosen_seed'] and chosen['groute_seed']==promotion['chosen_route_seed'] and checks['status']=='PASS';seeds['best_seed']=chosen['gplace_seed'];sta=parse(main/'report_timing/top.rtr');assert sta['status']=='PASS',sta
 for n,h in promotion['input_sha256'].items():assert sha(ROOT/n)==h,n
 assert sha(main/'new_core.tcl')==promotion['tcl_sha256']
 checkpoint=main/'checkpoints';cp=read(checkpoint/'clock82_checkpoint.json')
 assert sha(checkpoint/'clock82_checkpoint.json')==promotion['checkpoint_manifest_sha256']
 for n,h in cp['checkpoint_sha256'].items():assert sha(checkpoint/n)==h,n
 assert sha(main/'device_map/top_map.adf')==cp['checkpoint_sha256']['clock82_map.adf']
 guard=read(ROOT/'simulation/results/clock82_guard_checks/result.json');assert guard['status']=='PASS'
 for n,h in guard['input_sha256'].items():assert sha(ROOT/n)==h,n
 normalized=lambda p:re.sub(r'\s+','',re.sub(r'/\*.*?\*/|//[^\n]*','',p.read_text(errors='replace'),flags=re.S))
 equivalence=compare(trial/'synthesize/top_syn.vm',main/'synthesize/top_syn.vm');assert equivalence['status']=='PASS'
 save(out/'main_netlist_equivalence.json',dict(equivalence,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in (trial/'synthesize/top_syn.vm',main/'synthesize/top_syn.vm',ROOT/'tools/compare_clock82_netlists.py')}))
 dm=(main/'device_map/top.dmr').read_text(errors='replace');resources={k:int(re.search(r'\| '+re.escape(k)+r'\s+\|\s+(\d+)',dm)[1]) for k in ('LUT','FF','Distributed RAM','DRM','APM')}
 assert resources=={'LUT':11013,'FF':4476,'Distributed RAM':709,'DRM':48,'APM':4},resources
 placed=routed_resources(main/'place_route/top.prr')
 old=read(out/'previous_accepted_dual_baseline.json');parent_hash=sha(out/'previous_accepted_dual_baseline.json');assert sha(ROOT/'docs/accepted_dual_baseline.json')==parent_hash
 perf=checks['performance'];cycles=int(perf['metrics']['Stats window cycles']);retired=int(perf['metrics']['Retired instructions']);assert cycles==2698740 and retired==2808261
 evidence=[main/'new_core.pds',main/'report_timing/top.rtr',main/'place_route/top_pnr.adf',main/'synthesize/top_syn.vm',checkpoint/'clock82_checkpoint.json',checkpoint/'clock82_map.adf',main/'new_core.tcl',ROOT/'tools/verify_clock82_checkpoint.py',ROOT/'tools/compare_clock82_netlists.py',ROOT/'simulation/results/clock82_guard_checks/result.json',out/'reproduction_result.json',out/'seed_results.json',out/'route_results.json',out/'selected_config.json',out/'main_netlist_equivalence.json',ROOT/'simulation/results/clock82_checks/result.json',out/'source_equivalence.json']
 now=datetime.now().astimezone().isoformat();main_result=dict(status='PASS',recorded_at=now,variant='dual_boundary_next_pairbranch_clock82',chosen_seed=seeds['best_seed'],configured_cpu_hz=82000000,uart_divisor=712,estimated_fmax_mhz=sta['estimated_fmax_mhz'],corners=sta['corners'],resources=resources,ipc=retired/cycles,coremark_stats_cycles=cycles,retired=retired,dual=perf['dual'],parent_descriptor_sha256=parent_hash,input_sha256=promotion['input_sha256'],evidence_sha256={str(p.relative_to(ROOT)):sha(p) for p in evidence},normalized_main_netlist_equals_seeded_netlist=True)
 save(out/'main_result.json',main_result)
 main_result.update(chosen_route_seed=promotion.get('chosen_route_seed',0),routed_resources=placed,resource_basis='resources: device_map/top.dmr; routed_resources: final place_route/top.prr including physical optimization',normalized_main_netlist_equals_seeded_netlist=equivalence['original_textual_equal'],complete_structural_connectivity_equivalent=True,ram_replica_instance_name_permutations=len(equivalence['renamed_replicas']));save(out/'main_result.json',main_result)
 ips={n:h for n,h in promotion['input_sha256'].items() if '/ipcore/' in n.replace('\\','/') or '/memory/' in n.replace('\\','/')};src={n:h for n,h in promotion['input_sha256'].items() if n not in ips};src['hardware/pds/new_core.tcl']=sha(main/'new_core.tcl')
 decision=dict(status='ACCEPTED_DUAL_DEVELOPMENT_BASELINE',variant=main_result['variant'],user_instruction='频率改到82，布局多试试几个seed，看看能不能收敛',recorded_at=now,recorded_date=now[:10],timezone='Asia/Shanghai',scope='User-requested physical clock change to real82MHz, selected full-corner passing seed and independently rerun active main project. CPU pipeline/admission/bypass unchanged. Earlier resource rewrites remain rejected.',source_directory='hardware/pds',source_layout='direct PDS project: source/{core,perips,sys_bus,top,source}/*.v; not flat isolated overrides',parent_descriptor_sha256=parent_hash,parent_descriptor_snapshot=str((out/'previous_accepted_dual_baseline.json').relative_to(ROOT)),configured_cpu_hz=82000000,requested_period_ns=1000/82,uart_divisor=712,chosen_place_seed=seeds['best_seed'],estimated_fmax_mhz=sta['estimated_fmax_mhz'],resources=resources,corners=sta['corners'],coremark_stats_cycles=cycles,retired=retired,ipc=retired/cycles,dual=perf['dual'],source_sha256=src,ip_sha256=ips,evidence_sha256={str(p.relative_to(ROOT)):sha(p) for p in evidence+[out/'main_result.json']},historical_descriptor_resolution=dict(original_path='docs/accepted_dual_baseline.json',sha256=parent_hash,snapshot_path=str((out/'previous_accepted_dual_baseline.json').relative_to(ROOT))),single_issue_reference_sha256=old['single_issue_reference_sha256'],single_issue_sta_sha256=old['single_issue_sta_sha256'],limits=['Routed setup/hold passes at genuine PLL82MHz; no board measurement or programming.', 'Fixed diagnostic firmware still prints75MHz time metadata; cycle counts and normalized per-MHz diagnostic are independent.', 'This promotion is clock/seed configuration only; core RTL unchanged. Existing registered-forward/control paths remain.'])
 save(ROOT/'docs/accepted_dual_baseline.json',decision)
 decision.update(chosen_route_seed=promotion.get('chosen_route_seed',0),routed_resources=placed,resource_basis=main_result['resource_basis']);save(ROOT/'docs/accepted_dual_baseline.json',decision)
 active=dict(main_result,status='SYNCHRONIZED_AND_VERIFIED',accepted_descriptor_sha256=sha(ROOT/'docs/accepted_dual_baseline.json'),project='hardware/pds/new_core.pds',build_entry='hardware/pds/new_core.tcl',previous_project_directory=promotion['previous_main_project'],accepted_source_snapshot='hardware/pds',note='Main rebuilt natively with chosen seed at actual82MHz; complete CPU logic remains adopted pairbranch. Open desktop PDS window must reload project.')
 save(ROOT/'docs/active_pds_baseline.json',active);save(main/'BASELINE.json',active)
 p=ROOT/'README.md';s=p.read_text(encoding='utf-8');s=s.replace('PLL **80 MHz**','PLL **82 MHz**',1)
 start=s.index('当前已采纳的双发开发基线为');end=s.index('\n\n',start)
 s=s[:start]+f'当前已采纳的双发开发基线为 **`{decision["variant"]}`**：原 pairbranch CPU 结构不变，真实 PLL **82 MHz**，布局 seed **{seeds["best_seed"]}**，多角 setup/hold 通过，估算 Fmax **{sta["estimated_fmax_mhz"]:.3f} MHz**、IPC **{retired/cycles:.6f}**，资源 **11013 LUT / 4476 FF / 709 分布 RAM / 48 DRM / 4 APM**。主工程位于 `hardware/pds`，见 [当前采纳记录](docs/accepted_dual_baseline.json) 与 [82MHz多seed报告](docs/clock82_multiseed_20261022/README.md)。此前 80 MHz 工程完整保存在 `hardware/pds80_before_clock82_20261022`，尚未上板。'+s[end:]
 s=s.replace('见 [同步验证](docs/pds_main_sync_20261022/README.md) 和','见 [82MHz多seed验证](docs/clock82_multiseed_20261022/README.md)、[此前目录同步记录](docs/pds_main_sync_20261022/README.md) 和',1);p.write_text(s,encoding='utf-8')
 print('VERIFIED_AND_PROMOTED main82, seed',seeds['best_seed'],'Fmax',sta['estimated_fmax_mhz'])
if __name__=='__main__':main()
