"""Verify promoted main project and publish its binding to the accepted baseline."""
from pathlib import Path
from datetime import datetime
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
 out=ROOT/'docs/pds_main_sync_20261022';prep=read(out/'prepared.json');a=read(out/'accepted_descriptor_snapshot.json');main=ROOT/'hardware/pds';ref=ROOT/prep['source_directory'];backup=ROOT/prep['previous_project_directory']
 assert sha(ROOT/'docs/accepted_dual_baseline.json')==prep['accepted_descriptor_sha256']
 for n,h in read(out/'before_manifest.json').items():assert sha(backup/n)==h,('old project changed',n)
 for n,x in prep['exact_rtl_mapping'].items():assert sha(main/n)==x['sha256'],n
 assert read(ROOT/'simulation/results/pds_main_sync/result.json')['status']=='PASS'
 assert read(out/'netlist_equivalence.json')['equal'] is True
 old_image=(ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex').as_posix().encode();new_image=(main/'memory/boot_interleaved.hex').as_posix().encode()
 for p in (ref/'ipcore').rglob('*'):
  if p.is_file() and p.suffix in ('.v','.idf'):
   target=main/'ipcore'/p.relative_to(ref/'ipcore');assert target.read_bytes().replace(new_image,old_image)==p.read_bytes(),('IP differs beyond INIT path',p)
 assert sha(main/'memory/boot.hex')==sha(ROOT/'sw/build/boot.hex') and sha(main/'memory/boot_interleaved.hex')==sha(ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex')
 # Verify every GUI design/IP input resolves to the active project itself.
 project=main/'new_core.pds';text=project.read_text();setup=text.split('(_task tsk_compile',1)[0]
 paths=re.findall(r'\(_(?:file|ip|ip_source_item) "([^"]+)"',setup)
 for n in paths:
  p=(main/n).resolve();assert p.is_file() and p.is_relative_to(main.resolve()),('external/missing GUI input',n)
 assert len([n for n in paths if n.startswith('source/')])==17
 assert 'simulation/results/' not in (main/'new_core.tcl').read_text()
 sta=(main/'report_timing/top.rtr').read_text(errors='replace');resources=(main/'device_map/top.dmr').read_text(errors='replace');corners={}
 for name in ('Setup Summary(Slow Corner)','Hold Summary(Slow Corner)','Setup Summary(Fast Corner)','Hold Summary(Fast Corner)'):
  b=sta.split(name+':',1)[1].split('====',1)[0];m=re.search(r'\n\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(\d+)\s+(\d+)',b);assert m,name;corners[name]=dict(worst_slack_ns=float(m[1]),failing_endpoints=int(m[3]))
 measured={k:int(re.search(r'\| '+re.escape(k)+r'\s+\|\s+(\d+)',resources)[1]) for k in ('LUT','FF','Distributed RAM','DRM','APM')};assert measured==a['resources'],(measured,a['resources'])
 freq=re.search(r'(\d+\.\d+) MHz\s+(\d+\.\d+) MHz',sta);assert freq
 assert 'All Constraints Met.' in sta and all(v['worst_slack_ns']>=0 and v['failing_endpoints']==0 for v in corners.values()),corners
 assert '12.500' in sta and '.CLOCK_HZ(80000000)' in (main/'source/source/top.v').read_text()
 inputs=[p for folder in ('source','ipcore','constraints','memory') for p in (main/folder).rglob('*') if p.is_file() and p.suffix in ('.v','.idf','.fdc','.hex')]+[main/'new_core.tcl']
 record=dict(status='SYNCHRONIZED_AND_VERIFIED',recorded_at=datetime.now().astimezone().isoformat(),user_instruction='你现在同步一下',variant=a['variant'],accepted_descriptor_sha256=prep['accepted_descriptor_sha256'],project='hardware/pds/new_core.pds',build_entry='hardware/pds/new_core.tcl',accepted_source_snapshot=prep['source_directory'],previous_project_directory=prep['previous_project_directory'],configured_cpu_hz=80000000,estimated_fmax_mhz=float(freq[2]),corners=corners,resources=measured,coremark_stats_cycles=a['coremark_stats_cycles'],retired=a['retired'],ipc=a['ipc'],performance_evidence='Reused by byte-identical complete CPU/SoC RTL and normalized complete vendor mapped-netlist equality; active-project 6-case integration replay PASS. Main PDS compile/synthesize/map/route/STA freshly rerun.',input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs},evidence_sha256={str(p.relative_to(ROOT)):sha(p) for p in [project,main/'report_timing/top.rtr',main/'synthesize/top_syn.vm',main/'place_route/top_pnr.adf',ROOT/'simulation/results/pds_main_sync/result.json',out/'netlist_equivalence.json']},limits=['No board programming or measurement. Bitstream generation not requested.', 'Historical immutable baseline descriptors keep old hardware/pds paths; use pre-sync backup and before manifest to resolve those historical inputs. Pre-existing old PLL IDF drift is recorded in prepared.json.'])
 save(out/'result.json',record);save(ROOT/'docs/active_pds_baseline.json',record);save(main/'BASELINE.json',record)
 # Freeze source/evidence hashes here without copying multi-GB build caches.
 for p in [ROOT/'tools/prepare_pds_main_sync.py',ROOT/'tools/check_pds_main_sync.py',Path(__file__).resolve()]:shutil.copyfile(p,out/p.name)
 notes=['# 主 PDS 工程同步','', '`hardware/pds/new_core.pds` 已同步为当前采纳的 `dual_boundary_next_pairbranch` 双发基线，今后打开此入口。原工程完整保存在 `hardware/pds_before_pairbranch_20261022`，切换前全部文件 SHA 已复核。','', f'主工程重新编译、综合、映射、布局布线和 STA 通过：PLL 80 MHz，估算 Fmax {record["estimated_fmax_mhz"]:.3f} MHz；资源 {measured["LUT"]} LUT / {measured["FF"]} FF / {measured["Distributed RAM"]} 分布 RAM / {measured["DRM"]} DRM / {measured["APM"]} APM。四角 setup/hold 见 result.json。','', '全部 17 个 RTL 文件逐字节匹配采纳版；完整综合网表删除注释和空白后 SHA 完全相同，包括紫光 RAM 的原语 INIT 常量。主工程自带 memory/boot.hex 和正确的 A64/B32 编码 boot_interleaved.hex，16384 个 RV32 字逐字核对；仅改 IP 的 INIT_FILE 路径，构建不再依赖 simulation/results 中的源码或镜像。','', '实际主工程文件列表直接跑 6 项核心/SoC 集成测试通过，没有用独立候选源码覆盖。由于 RTL 和完整综合网表一致，IPC 和旧采纳版 CoreMark 结果按精确等价复用；未重新声称上板或正式 CoreMark 分数。','', '本次同步未纳入已经拒绝的四种资源改写。采纳描述和冻结试验归档不回写；新的主工程绑定以 docs/active_pds_baseline.json 和 hardware/pds/BASELINE.json 为准。旧单发源码的历史 hardware/pds 路径已迁到 backup，不能用新的主工程文件去校验旧单发哈希。','']
 (out/'README.md').write_text('\n'.join(notes),encoding='utf-8')
 readme=ROOT/'README.md';s=readme.read_text(encoding='utf-8');lead='当前主 PDS 工程为 [hardware/pds/new_core.pds](hardware/pds/new_core.pds)，已同步采纳的 **pairbranch 双发基线**，PLL **80 MHz**。工程源码、IP 和 CoreMark 初始化镜像均位于 `hardware/pds` 内。构建入口为 `hardware/pds/new_core.tcl`，见 [同步验证](docs/pds_main_sync_20261022/README.md) 和 [主工程基线绑定](docs/active_pds_baseline.json)。旧工程完整保存在 `hardware/pds_before_pairbranch_20261022`。\n\n'
 s=s.replace('# new_core\n\n','# new_core\n\n'+lead,1)
 s=s.replace('源码位于 `simulation/results/load_bp_dual_boundary_next_pairbranch`','采纳快照位于 `simulation/results/load_bp_dual_boundary_next_pairbranch`；主工程已同步到 `hardware/pds`')
 s=s.replace('及原 `hardware/pds` 单发工程保留对照','及迁移后的 `hardware/pds_before_pairbranch_20261022` 单发工程保留对照')
 marker='面向紫光同创 PGL50H-6 FBG484';pos=s.index(marker);s=s[:pos]+'以下早期单发设计说明为历史资料；当前双发工程以文首主入口和基线记录为准。\n\n'+s[pos:];readme.write_text(s,encoding='utf-8')
 save(out/'manifest.json',{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='manifest.json'})
 print('SYNCHRONIZED',record['project'],record['estimated_fmax_mhz'],'MHz',measured)
if __name__=='__main__':main()
