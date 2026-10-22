"""Record explicit storewrite adoption; keep frozen experiments immutable."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
 current=ROOT/'docs/accepted_dual_baseline.json';previous=read(current);parent_hash=sha(current);assert previous['variant']=='dual_boundary_slots'
 src=ROOT/'simulation/results/load_bp_dual_boundary_storewrite';archive=ROOT/'docs/dual_store_simple';dest=ROOT/'docs/dual_store_simple_adoption';assert not dest.exists()
 manifests={}
 for name in ('dual_store_simple','dual_mem_ipc','dual_timing80'):
  d=ROOT/'docs'/name;m=read(d/'manifest.json')
  for n,h in m.items():assert sha(d/n)==h,(name,n)
  manifests[name]=m
 comparison=read(archive/'comparison.json');assert comparison['preferred_candidate']=='dual_boundary_storewrite' and comparison['accepted_descriptor_sha256']==parent_hash
 for key in ('source_sha256','ip_sha256','evidence_sha256'):
  for n,h in previous[key].items():assert sha(ROOT/n)==h,(key,n)
 g=read(src/'generation.json');pd=read(src/'pds/result.json');perf=read(src/'performance/result.json');assert g['accepted_dual_sha256']==parent_hash and pd['status']=='PASS' and pd['pds_exit_code']==0
 for c in pd['corners'].values():assert c['failing_endpoints']==0 and c['worst_slack_ns']>=0
 assert pd['estimated_fmax_mhz']==80.535 and int(perf['metrics']['Stats window cycles'])==2704650 and int(perf['metrics']['Retired instructions'])==2808261
 for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
 def verify(x,label,parent_snapshot=None):
  for key in ('input_sha256','actual_compile_sha256','ip_sha256'):
   for n,h in x.get(key,{}).items():
    p=ROOT/n
    if not p.exists() and n.replace('\\','/').startswith('tmp/'):p=ROOT.parent/n
    if parent_snapshot is not None and p==current and h==parent_hash:p=parent_snapshot
    assert p.is_file() and sha(p)==h,(label,n)
 verify(g,'generation');verify(pd,'PDS');assert sha(src/'pds/run.tcl')==pd['tcl_sha256'];assert '12.500' in (src/'pds/report_timing/top.rtr').read_text(errors='replace')
 evidence=[src/'generation.json',src/'pds/run.tcl',src/'pds/report_timing/top.rtr',archive/'manifest.json']
 expected={'checks':63,'pair_checks':6,'cancel_checks':4,'audit_checks':4,'timeline_checks':4,'posted_module':8,'posted_soc_final':6,'publication_proof':1,'bus_induction':1,'simple_proof':1}
 for p in src.rglob('result.json'):
  if 'obj' in p.parts:continue
  x=read(p);assert x['status']=='PASS',(p,x['status']);verify(x,str(p))
  if p.parent.name in expected:assert len(x['tests'])==expected[p.parent.name]
  evidence.append(p)
 for sub in (*expected,'performance','validation','uart80','mem_paths'):assert (src/sub/'result.json').exists(),sub
 reproduction=ROOT/'simulation/results/dual_store_simple_verify/result.json';verify(read(reproduction),'regeneration');assert read(reproduction)['status']=='PASS';evidence.append(reproduction)
 # Unchanged core/MEM/operands retain exact earlier protocol evidence; real
 # posted-enabled SoC integration and all-state bus checks were rerun above.
 ref=ROOT/'simulation/results/load_bp_dual_boundary_storeack'
 for n in ('nc_core.v','nc_memory.v','nc_operands.v','nc_soc.v'):assert sha(src/n)==sha(ref/n),n
 reused={}
 for sub,count in (('dual_checks',7),('protocol',8),('mul_protocol',4),('memory_checks',4),('address_contract',10)):
  p=ref/sub/'result.json';x=read(p);assert x['status']=='PASS' and len(x['tests'])==count;verify(x,sub);evidence.append(p);reused[sub]=str(p.relative_to(ROOT))
 operand=ROOT/'simulation/results/load_bp_dual_boundary_slots/operand_checks/result.json';assert sha(src/'nc_operands.v')==sha(operand.parent.parent/'nc_operands.v');assert read(operand)['cycles']==300000;verify(read(operand),'operand');evidence.append(operand)
 assert sha(ROOT/'docs/accepted_baseline.json')==previous['single_issue_reference_sha256'];assert sha(ROOT/'hardware/pds/report_timing/top.rtr')==previous['single_issue_sta_sha256']
 p=ROOT/'docs/dual_store_simple.md';report=p.read_text(encoding='utf-8');old='**推荐隔离候选 `dual_boundary_storewrite`：80 MHz多角setup/hold通过，IPC维持1.038308。尚未自动采纳**，当前已采纳描述仍是 `dual_boundary_slots`。';assert report.count(old)==1
 notice='**`dual_boundary_storewrite` 已按用户“采纳”指令成为后续双发开发基线**：80 MHz多角setup/hold通过，IPC1.038308。见 [当前采纳记录](accepted_dual_baseline.json) 和 [本次采纳记录](dual_store_simple_adoption/adoption.json)。'
 readme=ROOT/'README.md';s=readme.read_text(encoding='utf-8');marker='面向紫光同创 PGL50H-6 FBG484';assert s.count(marker)==1;tail=s[s.index(marker):]
 tail=tail.replace('现已按用户指令采纳 `dual_boundary_slots`，后续优化从本版继续。','`dual_boundary_slots` 为历史采纳版本；现由 `dual_boundary_storewrite` 作为后续优化基线。')
 dest.mkdir();shutil.copyfile(current,dest/'previous_accepted_dual_baseline.json');shutil.copyfile(Path(__file__),dest/Path(__file__).name)
 now=datetime.now(timezone(timedelta(hours=8)));decision=dict(status='ACCEPTED_DUAL_DEVELOPMENT_BASELINE',variant='dual_boundary_storewrite',user_instruction='采纳',recorded_date=now.date().isoformat(),recorded_at=now.isoformat(),timezone='Asia/Shanghai',scope='Accepted local store quick completion plus simplified MMIO write control; isolated PLL80/UART80 source is subsequent dual-issue development baseline. Original hardware/pds single-issue reference retained. No board deployment.',source_directory=str(src.relative_to(ROOT)),parent_descriptor_sha256=parent_hash,parent_descriptor_snapshot=str((dest/'previous_accepted_dual_baseline.json').relative_to(ROOT)),configured_cpu_hz=80000000,requested_period_ns=12.5,uart_divisor=694,estimated_fmax_mhz=pd['estimated_fmax_mhz'],resources=pd['resources'],corners=pd['corners'],coremark_stats_cycles=2704650,retired=2808261,ipc=2808261/2704650,dual=perf['dual'],source_sha256=pd['input_sha256'],override_sha256=g['override_sha256'],ip_sha256=g['ip_sha256'],evidence_sha256={str(p.relative_to(ROOT)):sha(p) for p in evidence},reused_exact_source_evidence=reused,historical_descriptor_resolution=dict(original_path=str(current.relative_to(ROOT)),sha256=parent_hash,snapshot_path=str((dest/'previous_accepted_dual_baseline.json').relative_to(ROOT)),note='Historical generation and verification inputs refer to predecessor descriptor; resolve that exact hash against this snapshot, not the new current descriptor.'),single_issue_reference_sha256=previous['single_issue_reference_sha256'],single_issue_sta_sha256=previous['single_issue_sta_sha256'],limits=['Routed80MHz internal timing passes; worst setup0.083ns and hold0.019ns, small margin; no board measurement.', 'Fixed CoreMark images retain75MHz print metadata; IPC is independent retired/cycles, not a formal benchmark score.', 'POST_LOCAL_STORES enabled only for fixed no-late-error local BRAM bus; generic core defaults OFF. Existing15-level early-load RAM enable path remains.', 'storelogic range/predicate rewrite was not adopted. Frozen experiment reports retain their original trial status.'])
 save(dest/'accepted_dual_baseline.json',decision);save(current,decision)
 save(dest/'adoption.json',dict(status=decision['status'],variant=decision['variant'],user_instruction='采纳',recorded_at=now.isoformat(),accepted_descriptor_sha256=sha(current),previous_descriptor_sha256=parent_hash,source_directory=decision['source_directory'],next_development_baseline=decision['variant'],verified_archived_files={n:len(m) for n,m in manifests.items()},historical_archive_manifest_sha256=sha(archive/'manifest.json'),adoption_tool_sha256=sha(Path(__file__))))
 p.write_text(report.replace(old,notice).replace('| 当前采纳slots |','| 历史采纳slots |')+'\n采纳记录独立保存；`dual_store_simple/` 内冻结报告、比较数据和manifest保留试验完成时的状态，不回写归档。\n',encoding='utf-8')
 intro='# new_core\n\n当前已采纳的双发开发基线为 **`dual_boundary_storewrite`**：80 MHz配置，多角setup/hold通过，估算Fmax **80.535 MHz**、IPC **1.038308**；资源 **10843 LUT / 4476 FF / 709 分布RAM / 48 DRM / 4 APM**。源码与PLL80位于 `simulation/results/load_bp_dual_boundary_storewrite`，见 [当前采纳记录](docs/accepted_dual_baseline.json)、[本次采纳记录](docs/dual_store_simple_adoption/adoption.json) 和 [统一报告](docs/dual_store_simple.md)。最差setup/hold余量0.083/0.019 ns，尚未上板。\n\n此前store快速完成试验见 [MEM等待与IPC试验](docs/dual_mem_ipc.md)；其中三版当时均未达到80 MHz，本次仅采纳后续MMIO写控制简化版。上一采纳版本 `dual_boundary_slots` 及原 `hardware/pds` 单发工程保留对照。\n\n'
 readme.write_text(intro+tail,encoding='utf-8')
 for name,m in manifests.items():
  for n,h in m.items():assert sha(ROOT/'docs'/name/n)==h,(name,n)
 for n,h in decision['evidence_sha256'].items():assert sha(ROOT/n)==h,n
 verify(read(reproduction),'historical regeneration after adoption',dest/'previous_accepted_dual_baseline.json')
 assert sha(current)==sha(dest/'accepted_dual_baseline.json') and read(current)['variant']=='dual_boundary_storewrite'
 save(dest/'manifest.json',{str(p.relative_to(dest)):sha(p) for p in sorted(dest.iterdir()) if p.is_file()})
 print('ACCEPTED dual_boundary_storewrite; archives, source, evidence and references verified')
if __name__=='__main__':main()
