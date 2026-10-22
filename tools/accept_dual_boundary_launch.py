"""Append a new adoption record, preserving the previous immutable archive."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
 old=ROOT/'docs/accepted_dual_baseline.json';src=ROOT/'simulation/results/load_bp_dual_boundary_launch'
 assert read(old)['variant']=='dual_fwd_share'
 archive=ROOT/'docs/dual_boundary'
 for n,h in read(archive/'manifest.json').items():assert sha(archive/n)==h,n
 g=read(src/'generation.json');pds=read(src/'pds/result.json');perf=read(src/'performance/result.json')
 for n,h in pds['input_sha256'].items():assert sha(ROOT/n)==h,n
 for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
 evidence=[src/'generation.json',src/'pds/result.json',src/'pds/report_timing/top.rtr']
 for sub in ('performance','validation','checks','dual_checks','pair_checks','cancel_checks','audit','timeline_checks','memory_checks','address_contract'):
  p=src/sub/'result.json'
  if not p.exists():continue
  assert read(p)['status']=='PASS',sub
  evidence.append(p)
 dest=ROOT/'docs/dual_boundary_adoption';dest.mkdir(exist_ok=False);shutil.copyfile(old,dest/'previous_accepted_dual_baseline.json')
 previous=read(old);decision=dict(status='ACCEPTED_DUAL_DEVELOPMENT_BASELINE',variant='dual_boundary_launch',user_instruction='采纳，接下来请优化时序，目标是80MHz',recorded_date='2026-10-21',timezone='Asia/Shanghai',scope='Accepted dual development source in simulation/results; hardware/pds single-issue reference and historical archives preserved. This accepted source still uses PLL 75MHz.',source_directory=str(src.relative_to(ROOT)),parent_descriptor_sha256=sha(old),estimated_fmax_mhz=pds['estimated_fmax_mhz'],resources=pds['resources'],corners=pds['corners'],coremark_stats_cycles=int(perf['metrics']['Stats window cycles']),retired=int(perf['metrics']['Retired instructions']),ipc=int(perf['metrics']['Retired instructions'])/int(perf['metrics']['Stats window cycles']),dual=perf['dual'],source_sha256=pds['input_sha256'],override_sha256=g['override_sha256'],ip_sha256=g['ip_sha256'],evidence_sha256={str(p.relative_to(ROOT)):sha(p) for p in evidence},single_issue_reference_sha256=previous['single_issue_reference_sha256'],single_issue_sta_sha256=previous['single_issue_sta_sha256'])
 save(old,decision);save(dest/'accepted_dual_baseline.json',decision)
 save(dest/'adoption.json',dict(user_instruction=decision['user_instruction'],historical_archive_manifest_sha256=sha(archive/'manifest.json'),verified_archived_files=len(read(archive/'manifest.json')),accepted_descriptor_sha256=sha(old)))
 p=ROOT/'README.md';s=p.read_text(encoding='utf-8');s+='\n2026-10-21 最新采纳：`dual_boundary_launch`，IPC 1.000230、PDS Fmax 77.760 MHz、11498 LUT / 4495 FF / 709 分布RAM / 48 DRM / 4 APM。当前双发源位于 `simulation/results/load_bp_dual_boundary_launch`；见 [当前采纳记录](docs/accepted_dual_baseline.json) 与 [本次采纳记录](docs/dual_boundary_adoption/adoption.json)。此前各轮记录为历史结论。下一轮目标为80 MHz，原75 MHz PLL和单发工程保留。\n';p.write_text(s,encoding='utf-8')
 print('ACCEPTED dual_boundary_launch; historical archive verified and preserved')
if __name__=='__main__':main()
