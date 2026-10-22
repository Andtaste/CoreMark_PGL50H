"""Verify this published snapshot and run its native PDS build."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,sys,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--pds-home',type=Path,default=Path(os.environ.get('PDS_HOME','E:/pango/PDS_2022.2-SP1-Lite')));p.add_argument('--verify-only',action='store_true');a=p.parse_args()
 release=json.loads((ROOT/'docs/published_release.json').read_text(encoding='utf-8'));project=ROOT/'hardware/pds'
 for n,h in release['source_input_sha256'].items():assert sha(ROOT/n)==h,n
 assert len(release['cpu_rtl_sha256'])==17
 for n,h in release['cpu_rtl_sha256'].items():assert sha(ROOT/n)==h,n
 if release['branch']=='main':
  cp=json.loads((project/'checkpoints/clock82_checkpoint.json').read_text())
  for n,h in cp['checkpoint_sha256'].items():assert sha(project/'checkpoints'/n)==h,n
 if a.verify_only:print('PASS published input hashes, unchanged17 RTL files and applicable82MHz checkpoint');return
 output=ROOT/'simulation/results/release_checks';output.mkdir(parents=True,exist_ok=True);env=os.environ.copy();env['NEW_CORE_PYTHON']=sys.executable;env['PYTHONUTF8']='1';env.pop('NC_CLOCK82_ROUTE_ONLY',None)
 with (output/'pds_build.log').open('wb') as stream:
  def native(script):
   result=subprocess.run([str(a.pds_home/'bin/pds_shell.exe'),'-f',script],cwd=project,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=3600)
   assert result.returncode==0,'Native PDS failed; see simulation/results/release_checks/pds_build.log'
  native('new_core.tcl')
  if release['branch']=='main':
   subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools/verify_clock82_checkpoint.py'),'--project',str(project),'--install'],env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
   native('route_verified.tcl')
 report=project/'report_timing/top.rtr';text=report.read_text(errors='replace');corners={}
 for name in ('Setup Summary(Slow Corner)','Hold Summary(Slow Corner)','Setup Summary(Fast Corner)','Hold Summary(Fast Corner)'):
  block=text.split(name+':',1)[1].split('====',1)[0];m=re.search(r'\n\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(\d+)\s+(\d+)',block);assert m,name;corners[name]=dict(slack_ns=float(m[1]),failing_endpoints=int(m[3]))
 m=re.search(r'(\d+\.\d+) MHz\s+(\d+\.\d+) MHz\s+(\d+\.\d+)\s+(\d+\.\d+)',text);assert m
 assert abs(float(m[1])-release['configured_cpu_hz']/1e6)<.01,'Wrong PLL-generated clock'
 assert 'All Constraints Met.' in text and all(x['slack_ns']>=0 and not x['failing_endpoints'] for x in corners.values()),corners
 if release['branch']=='main':assert sha(project/'device_map/top_map.adf')==cp['checkpoint_sha256']['clock82_map.adf']
 dest=ROOT/'docs/published_build';dest.mkdir(parents=True,exist_ok=True)
 for src,name in ((report,'timing.rtr'),(project/'device_map/top.dmr','resources.dmr'),(project/'place_route/top.prr','place_route.prr')):shutil.copyfile(src,dest/name)
 record=dict(status='PASS',scope='Native build in independent publication checkout after path-only portability edits; no board programming',configured_cpu_hz=release['configured_cpu_hz'],reported_clock_mhz=float(m[1]),estimated_fmax_mhz=float(m[2]),corners=corners,source_input_sha256=release['source_input_sha256'],build_entry_sha256=sha(project/'new_core.tcl'),reports_sha256={f.name:sha(f) for f in dest.iterdir() if f.is_file()},checkpoint_reused_after_source_and_connectivity_verification=release['branch']=='main')
 (dest/'result.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS published',release['branch'],'native build at',release['configured_cpu_hz'],'Hz; estimated Fmax',m[2],flush=True)
if __name__=='__main__':main()
