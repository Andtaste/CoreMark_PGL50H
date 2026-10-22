"""Record explicit adoption without rewriting frozen timing experiment evidence."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
 current=ROOT/'docs/accepted_dual_baseline.json';previous=read(current)
 assert previous['variant']=='dual_boundary_launch'
 src=ROOT/'simulation/results/load_bp_dual_boundary_slots';archive=ROOT/'docs/dual_timing80'
 manifest=read(archive/'manifest.json')
 for n,h in manifest.items():assert sha(archive/n)==h,n
 comparison=read(archive/'comparison.json');assert comparison['preferred_candidate']=='dual_boundary_slots'
 assert comparison['accepted_descriptor_sha256']==sha(current)
 g=read(src/'generation.json');pd=read(src/'pds/result.json');perf=read(src/'performance/result.json')
 assert pd['status']=='PASS' and pd['pds_exit_code']==0
 for c in pd['corners'].values():assert c['failing_endpoints']==0 and c['worst_slack_ns']>=0
 for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
 for key in ('input_sha256','ip_sha256'):
  for x in (g,pd):
   for n,h in x.get(key,{}).items():assert sha(ROOT/n)==h,n
 evidence=[src/'generation.json',src/'pds/result.json',src/'pds/run.tcl',src/'pds/report_timing/top.rtr',src/'timing_paths/result.json',archive/'manifest.json']
 expected={'checks':63,'dual_checks':7,'pair_checks':6,'cancel_checks':4,'audit_checks':4,'timeline_checks':4,'memory_checks':4,'address_contract':10,'protocol':8,'mul_protocol':4,'operand_checks':3}
 for sub in [*expected,'performance','validation','slots_metrics','slots_reproduce','uart80']:
  p=src/sub/'result.json';x=read(p);assert x['status']=='PASS',sub
  if sub in expected:assert len(x['tests'])==expected[sub],sub
  for key in ('input_sha256','actual_compile_sha256','ip_sha256'):
   for n,h in x.get(key,{}).items():assert sha(ROOT/n)==h,(sub,n)
  evidence.append(p)
 assert '12.500' in (src/'pds/report_timing/top.rtr').read_text(errors='replace')
 assert sha(ROOT/'docs/accepted_baseline.json')==previous['single_issue_reference_sha256']
 assert sha(ROOT/'hardware/pds/report_timing/top.rtr')==previous['single_issue_sta_sha256']
 dest=ROOT/'docs/dual_timing80_adoption';assert not dest.exists();dest.mkdir()
 shutil.copyfile(current,dest/'previous_accepted_dual_baseline.json')
 now=datetime.now(timezone(timedelta(hours=8)))
 cycles=int(perf['metrics']['Stats window cycles']);retired=int(perf['metrics']['Retired instructions'])
 decision=dict(status='ACCEPTED_DUAL_DEVELOPMENT_BASELINE',variant='dual_boundary_slots',user_instruction='采纳推荐版本',recorded_date=now.date().isoformat(),recorded_at=now.isoformat(),timezone='Asia/Shanghai',scope='Accepted source and isolated PLL80/UART80 implementation for subsequent dual-issue development. Source in simulation/results; hardware/pds single-issue reference and historical archives preserved. No board deployment.',source_directory=str(src.relative_to(ROOT)),parent_descriptor_sha256=sha(current),configured_cpu_hz=80000000,requested_period_ns=12.5,uart_divisor=694,estimated_fmax_mhz=pd['estimated_fmax_mhz'],resources=pd['resources'],corners=pd['corners'],coremark_stats_cycles=cycles,retired=retired,ipc=retired/cycles,dual=perf['dual'],source_sha256=pd['input_sha256'],override_sha256=g['override_sha256'],ip_sha256=g['ip_sha256'],evidence_sha256={str(p.relative_to(ROOT)):sha(p) for p in evidence},single_issue_reference_sha256=previous['single_issue_reference_sha256'],single_issue_sta_sha256=previous['single_issue_sta_sha256'],limits=['Routed STA at80MHz passes; worst setup0.055ns and hold0.120ns. No board validation.', 'Fixed diagnostic images retain75MHz print metadata; comparison uses independent cycle counters. CPU IPC1.000230 unchanged.', 'Generation reused_operand_sha256 is inherited historical metadata; actual operand override hash and new300000-cycle independent equivalence identify the accepted implementation.'])
 save(dest/'accepted_dual_baseline.json',decision);save(current,decision)
 save(dest/'adoption.json',dict(status=decision['status'],variant=decision['variant'],user_instruction=decision['user_instruction'],recorded_at=decision['recorded_at'],accepted_descriptor_sha256=sha(current),historical_archive_manifest_sha256=sha(archive/'manifest.json'),verified_archived_files=len(manifest),source_directory=decision['source_directory'],next_development_baseline='dual_boundary_slots'))
 p=ROOT/'README.md';s=p.read_text(encoding='utf-8')
 s=s.replace('当前已采纳的双发开发基线为 `dual_fwd_share`','历史采纳版本 `dual_fwd_share`（已被后续版本替代）')
 s=s.replace('2026-10-21 最新采纳：`dual_boundary_launch`','2026-10-21 历史采纳：`dual_boundary_launch`')
 s=s.replace('本轮尚未采纳；当前已采纳双发开发基线仍为 `dual_boundary_launch`。','现已按用户指令采纳 `dual_boundary_slots`，后续优化从本版继续。')
 notice='当前已采纳的双发开发基线为 **`dual_boundary_slots`**：80 MHz配置，多角setup/hold通过，估算Fmax **80.354 MHz**、IPC **1.000230**；资源 **11005 LUT / 4475 FF / 709 分布RAM / 48 DRM / 4 APM**。源码与PLL80位于 `simulation/results/load_bp_dual_boundary_slots`，见 [当前采纳记录](docs/accepted_dual_baseline.json)、[本次采纳记录](docs/dual_timing80_adoption/adoption.json) 和 [时序报告](docs/dual_timing80.md)。最差setup余量0.055 ns，尚未上板；原 `hardware/pds` 单发工程及下文历史记录保留对照。\n'
 first,sep,rest=s.partition('\n');s=first+'\n\n'+notice+'\n'+rest;p.write_text(s,encoding='utf-8')
 p=ROOT/'docs/dual_timing80.md';s=p.read_text(encoding='utf-8');s=s.replace('本轮为其上的隔离时序试验，尚未自动替换采纳描述。','本轮推荐版 `dual_boundary_slots` 已按用户“采纳推荐版本”指令成为后续双发开发基线，见 `accepted_dual_baseline.json` 和 `dual_timing80_adoption/adoption.json`。')
 s+='\n采纳记录独立保存；`dual_timing80/` 内报告、对比状态和manifest保持试验完成时的历史内容，不回写归档。\n';p.write_text(s,encoding='utf-8')
 for n,h in manifest.items():assert sha(archive/n)==h,n
 for n,h in decision['evidence_sha256'].items():assert sha(ROOT/n)==h,n
 assert read(current)['variant']=='dual_boundary_slots' and sha(current)==sha(dest/'accepted_dual_baseline.json')
 print('ACCEPTED dual_boundary_slots; verified',len(manifest),'frozen files; baseline source/evidence verified; reference preserved')
if __name__=='__main__':main()
