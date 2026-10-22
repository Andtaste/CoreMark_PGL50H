"""Record the user's pairbranch adoption without changing frozen trial bytes."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib, json, shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x): p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
 current=ROOT/'docs/accepted_dual_baseline.json'; old=read(current); parent=sha(current)
 assert old['variant']=='dual_boundary_storewrite'
 archive=ROOT/'docs/dual_next_trials'; manifest=read(archive/'manifest.json')
 for n,h in manifest.items(): assert sha(archive/n)==h,n
 # Historical comparison contains lossy legacy-console Chinese text. Its
 # byte hash above is authoritative; decision/metrics are ASCII JSON fields.
 comparison=json.loads((archive/'comparison.json').read_text(encoding='utf-8-sig',errors='replace'))
 assert comparison['preferred_candidate']=='pairbranch' and comparison['accepted_descriptor_sha256']==parent
 src=ROOT/'simulation/results/load_bp_dual_boundary_next_pairbranch'
 g=read(src/'generation.json'); pd=read(src/'pds/result.json'); perf=read(src/'performance/result.json')
 assert g['accepted_dual_sha256']==parent and pd['status']=='PASS' and pd['pds_exit_code']==0
 assert int(perf['metrics']['Stats window cycles'])==2698740 and int(perf['metrics']['Retired instructions'])==2808261
 assert all(c['worst_slack_ns']>=0 and c['failing_endpoints']==0 for c in pd['corners'].values())
 for n,h in pd['input_sha256'].items(): assert sha(ROOT/n)==h,n
 for n,h in g['override_sha256'].items(): assert sha(src/Path(n).name)==h,n
 for n,h in g['ip_sha256'].items(): assert sha(ROOT/n)==h,n
 evidence=[src/'generation.json',src/'pds/run.tcl',src/'pds/report_timing/top.rtr',archive/'manifest.json']
 for sub in ('checks','validation','pair_checks','cancel_checks','audit_checks','protocol','mul_protocol','posted_soc_final','uart80','timeline_checks','next_directed','next_suite','performance','next_paths'):
  p=src/sub/'result.json'; assert read(p)['status']=='PASS',sub; evidence.append(p)
 for key in ('source_sha256','ip_sha256','evidence_sha256'):
  for n,h in old[key].items(): assert sha(ROOT/n)==h,n
 dest=ROOT/'docs/dual_pairbranch_adoption'; assert not dest.exists();dest.mkdir()
 shutil.copyfile(current,dest/'previous_accepted_dual_baseline.json')
 shutil.copyfile(Path(__file__),dest/Path(__file__).name)
 now=datetime.now(timezone(timedelta(hours=8)))
 decision=dict(status='ACCEPTED_DUAL_DEVELOPMENT_BASELINE',variant='dual_boundary_next_pairbranch',user_instruction='采纳推荐，顺便看看还能不能优化资源占用',recorded_date=now.date().isoformat(),recorded_at=now.isoformat(),timezone='Asia/Shanghai',scope='Accepted primary load/store plus conditional secondary branch admission. Same datapaths, FIFO depths, PLL80, posted-local-store contract and prediction algorithm. Subsequent resource trials remain unadopted.',source_directory=str(src.relative_to(ROOT)),parent_descriptor_sha256=parent,parent_descriptor_snapshot=str((dest/'previous_accepted_dual_baseline.json').relative_to(ROOT)),configured_cpu_hz=80000000,requested_period_ns=12.5,uart_divisor=694,estimated_fmax_mhz=pd['estimated_fmax_mhz'],resources=pd['resources'],corners=pd['corners'],coremark_stats_cycles=2698740,retired=2808261,ipc=2808261/2698740,dual=perf['dual'],source_sha256=pd['input_sha256'],override_sha256=g['override_sha256'],ip_sha256=g['ip_sha256'],evidence_sha256={str(p.relative_to(ROOT)):sha(p) for p in evidence},historical_descriptor_resolution=dict(original_path=str(current.relative_to(ROOT)),sha256=parent,snapshot_path=str((dest/'previous_accepted_dual_baseline.json').relative_to(ROOT))),single_issue_reference_sha256=old['single_issue_reference_sha256'],single_issue_sta_sha256=old['single_issue_sta_sha256'],limits=['No board measurement; fixed CoreMark diagnostic images retain old printed clock metadata.', 'Existing registered-forward/control/early-RAM-enable path remains; 80MHz routed four-corner checks pass.', 'Historical source comments about LSU plus MUL admission are stale; actual new admission is LSU plus conditional branch only. Tested source bytes deliberately retained.'])
 save(current,decision);save(dest/'accepted_dual_baseline.json',decision)
 save(dest/'adoption.json',dict(status=decision['status'],variant=decision['variant'],recorded_at=now.isoformat(),accepted_descriptor_sha256=sha(current),previous_descriptor_sha256=parent,verified_archive_files=len(manifest),archive_manifest_sha256=sha(archive/'manifest.json')))
 p=ROOT/'README.md';s=p.read_text(encoding='utf-8');start=s.index('当前已采纳的双发开发基线为');end=s.index('\n\n',start)
 s=s[:start]+'当前已采纳的双发开发基线为 **`dual_boundary_next_pairbranch`**：允许主槽 load/store 与副槽条件分支配对；80 MHz 配置，多角 setup/hold 通过，估算 Fmax **80.710 MHz**、IPC **1.040582**，资源 **11040 LUT / 4476 FF / 709 分布 RAM / 48 DRM / 4 APM**。源码位于 `simulation/results/load_bp_dual_boundary_next_pairbranch`，见 [当前采纳记录](docs/accepted_dual_baseline.json)、[本次采纳记录](docs/dual_pairbranch_adoption/adoption.json) 和 [试验报告](docs/dual_next_trials.md)。最差 setup/hold 余量 0.110/0.111 ns，尚未上板。'+s[end:]
 s=s.replace('当前基线仍为 `dual_boundary_storewrite`；','该轮以历史基线 `dual_boundary_storewrite` 为对照；')
 p.write_text(s,encoding='utf-8')
 for n,h in manifest.items(): assert sha(archive/n)==h,n
 assert sha(ROOT/'docs/accepted_baseline.json')==old['single_issue_reference_sha256']
 assert sha(ROOT/'hardware/pds/report_timing/top.rtr')==old['single_issue_sta_sha256']
 save(dest/'manifest.json',{str(p.relative_to(dest)):sha(p) for p in dest.iterdir() if p.is_file()})
 print('ACCEPTED',decision['variant'],'verified archived files',len(manifest))
if __name__=='__main__': main()
