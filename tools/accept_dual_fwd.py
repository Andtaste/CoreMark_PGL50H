"""Record the user's acceptance of the tested dual forwarding baseline."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
 dest=ROOT/'docs/dual_fwd';src=ROOT/'simulation/results/load_bp_dual_fwd_share'
 for n,h in read(dest/'manifest.json').items():assert sha(dest/n)==h,n
 g=read(src/'generation.json');pds=read(src/'pds/result.json');perf=read(src/'performance/result.json')
 for sub in ('pds','performance','validation','checks','dual_checks','audit','forwarding_equivalence','boundary_audit'):
  x=read(src/sub/'result.json');assert x['status']=='PASS',sub
  for key in ('input_sha256','actual_compile_sha256','ip_sha256'):
   for n,h in x.get(key,{}).items():assert sha(ROOT/n)==h,(sub,n)
 for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
 status='ACCEPTED_DUAL_DEVELOPMENT_BASELINE'
 decision=dict(status=status,variant='dual_fwd_share',user_instruction='很好，采纳',recorded_date='2026-10-21',timezone='Asia/Shanghai',
  scope='Accepted working baseline for subsequent dual-issue development. Original single-issue production checkout remains a preserved comparison/reference; no PLL or board deployment change.')
 save(dest/'adoption.json',decision)
 save(ROOT/'docs/accepted_dual_baseline.json',dict(**decision,source_directory=str(src.relative_to(ROOT)),
  estimated_fmax_mhz=pds['estimated_fmax_mhz'],resources=pds['resources'],corners=pds['corners'],
  coremark_stats_cycles=int(perf['metrics']['Stats window cycles']),retired=int(perf['metrics']['Retired instructions']),
  ipc=int(perf['metrics']['Retired instructions'])/int(perf['metrics']['Stats window cycles']),dual=perf['dual'],
  source_sha256=pds['input_sha256'],override_sha256=g['override_sha256'],ip_sha256=g['ip_sha256'],
  evidence_sha256={str(p.relative_to(ROOT)):sha(p) for p in (src/'generation.json',src/'pds/result.json',src/'pds/report_timing/top.rtr',src/'performance/result.json',src/'validation/result.json')},
  single_issue_reference_sha256=sha(ROOT/'docs/accepted_baseline.json'),single_issue_sta_sha256=sha(ROOT/'hardware/pds/report_timing/top.rtr')))
 report=ROOT/'docs/dual_fwd.md';s=report.read_text(encoding='utf-8')
 s=s.replace('本轮是试验和推荐，未替换正式单发基线或此前用户的双发保留记录。\n状态 RESEARCH_COMPLETE_NOT_ADOPTED，preferred_research_candidate=dual_fwd_share。',
  '用户于 2026-10-21 明确“很好，采纳”，现为后续双发开发基线，见 `accepted_dual_baseline.json` 和 `dual_fwd/adoption.json`。\n状态 ACCEPTED_DUAL_DEVELOPMENT_BASELINE，preferred_research_candidate=dual_fwd_share。\n此前单发工程和 84.710 MHz 历史归档保留作对照，后续双发优化从本版开始。')
 report.write_text(s,encoding='utf-8')
 readme=ROOT/'README.md';s=readme.read_text(encoding='utf-8')
 note='\n当前已采纳的双发开发基线为 `dual_fwd_share`：87.789 MHz、8339 LUT、4096 FF、705 分布式 RAM、48 DRM、4 APM；IPC 0.811941。源码与验证入口见 [双发采纳记录](docs/accepted_dual_baseline.json)。上文各轮研究结论为历史记录；`hardware/pds` 下原单发工程保留对照，当前双发源码位于 `simulation/results/load_bp_dual_fwd_share`。\n'
 if 'docs/accepted_dual_baseline.json' not in s:s+=note
 readme.write_text(s,encoding='utf-8')
 subprocess.run([sys.executable,str(ROOT/'tools/archive_dual_fwd.py'),'--preferred','dual_fwd_share'],cwd=ROOT,check=True)
 for n,h in read(dest/'manifest.json').items():assert sha(dest/n)==h,n
 print('ACCEPTED dual_fwd_share; source/evidence and archive verified; single-issue reference preserved')
if __name__=='__main__':main()
