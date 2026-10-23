"""Freeze the board-validated baseline and stage its Git main publication."""
from pathlib import Path
import hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
PUB=ROOT.parent/'tmp/github_newcore_publish_20261022/main'
SNAP=ROOT/'baselines/board83_validated_20261023'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def cp(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def main():
 assert not SNAP.exists()
 manifest=json.loads((ROOT/'hardware/pds/main_manifest.json').read_text())
 for n,h in manifest['input_sha256'].items():assert sha(ROOT/'hardware/pds'/n)==h,n
 assert sha(ROOT/'output/board83/top.sbit')=='6fda0a4e7f3d185d28fa719e4ca0da9b516b5a43a5ead92bb6f264fa4be97f79'
 shutil.copytree(ROOT/'hardware/pds',SNAP/'hardware/pds')
 for n in ('active_compiler_profile.json','active_optimization_baseline.json','main_board83_sync.json','report_compare_fix_status.json'):
  cp(ROOT/'docs'/n,SNAP/'docs'/n)
 record=dict(status='BOARD_VALIDATED_BASELINE',date='2026-10-23',project='hardware/pds',snapshot=str(SNAP.relative_to(ROOT)).replace('\\','/'),configured_cpu_hz=83000000,iterations=5000,benchmark_cycles=1149771717,stats_cycles=1149771754,retired_instructions=1270809719,coremark=360.941214,coremark_per_mhz=4.348689,ipc=1.105,cpi=.904,crc='PASS',counter_bounds='PASS',board_evidence='User-provided serial screenshot in this conversation; observed values exactly match corrected report replay.',bitstream_sha256=sha(ROOT/'output/board83/top.sbit'),priority=['throughput','clock_frequency','coremark_per_mhz','resources'],input_sha256=manifest['input_sha256'])
 save(SNAP/'baseline.json',record);save(ROOT/'docs/continuous_baseline_20261023.json',record)
 readme=ROOT/'README.md';s=readme.read_text(encoding='utf-8')
 s=s.replace('新文件尚未上板。','用户已用新文件完成实板复测：5000次CRC PASS，360.941214 CoreMark、4.348689 CM/MHz、IPC 1.105、CPI 0.904，计数边界PASS；与修复后预期一致。')
 readme.write_text(s,encoding='utf-8')
 assert subprocess.check_output(['git','status','--porcelain'],cwd=PUB)==b''
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=PUB)==subprocess.check_output(['git','rev-parse','origin/main'],cwd=PUB)
 # Keep accepted source byte-for-byte. Large local archives and generated caches
 # remain local; publish the current rebuild inputs, final bitstream and evidence.
 groups={'tools':{'.py','.ps1','.sh','.cmd','.bat'},'simulation/tb':{'.v','.sv'},'simulation/models':{'.v','.sv'},'simulation/scripts':{'.py','.ps1','.sh'},'simulation/tests':{'.S','.s','.c','.h','.ld'},'sw':{'.c','.h','.S','.s','.ld','.lds','.mk','.py','.md','.txt','.json'},'hardware/pds/source':{'.v'},'hardware/pds/ipcore':{'.v','.vhdl','.idf','.dat','.hex','.json'},'hardware/pds/constraints':{'.fdc'},'hardware/pds/memory':{'.hex','.md'},'output/board83':{'.sbit','.json'}}
 for folder,suffixes in groups.items():
  for p in (ROOT/folder).rglob('*'):
   if not p.is_file() or p.suffix not in suffixes and p.name not in ('Makefile','LICENSE'):continue
   if '__pycache__' in p.parts or any(x.startswith('rev_') for x in p.parts) or folder=='sw' and 'build' in p.relative_to(ROOT/'sw').parts:continue
   cp(p,PUB/p.relative_to(ROOT))
 for p in (ROOT/'docs').glob('*'):
  if p.is_file() and p.suffix in ('.json','.md','.txt'):cp(p,PUB/p.relative_to(ROOT))
 for n in ('README.md','open_main.cmd','hardware/pds/new_core.pds','hardware/pds/new_core.tcl','hardware/pds/main_manifest.json','hardware/pds/release_result.json','hardware/pds/README.txt','hardware/pds/generate_bitstream.tcl','hardware/pds/boot_interleaved.hex'):
  cp(ROOT/n,PUB/n)
 for folder in ('sw/build/coremark_performance_5000_continuous83_inline80_sweep','simulation/results/report_large_20261023'):
  for p in (ROOT/folder).glob('*'):
   if p.is_file() and p.suffix in ('.json','.hex','.uart','.log'):cp(p,PUB/p.relative_to(ROOT))
 for folder in ('report_timing','place_route','device_map'):
  for p in (ROOT/'hardware/pds'/folder).glob('*'):
   if p.suffix in ('.rtr','.prr','.dmr'):cp(p,PUB/'docs/board83_validated_20261023'/p.name)
 cp(ROOT/'hardware/pds/download/top.sbit',PUB/'hardware/pds/download/top.sbit')
 for n,h in manifest['input_sha256'].items():assert sha(PUB/'hardware/pds'/n)==h,n
 save(PUB/'docs/published_release.json',record|{'scope':'Current board-validated 83MHz sources, exact ROM and bitstream; supersedes historical82MHz build_release driver. Use tools/build_main.py or open_main.cmd.'})
 print('SNAPSHOT',SNAP,flush=True);print('PUBLICATION_STAGED',PUB,flush=True)
if __name__=='__main__':main()
