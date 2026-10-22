"""Rebuild the frozen board5000 source with its own verified mapping and generate SRAM bitstream."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--verify-only',action='store_true');p.add_argument('--pds-home',type=Path,default=Path(os.environ.get('PDS_HOME','E:/pango/PDS_2022.2-SP1-Lite')));a=p.parse_args()
 manifest=json.loads((ROOT/'docs/board5000_20261022/board_manifest.json').read_text());project=ROOT/manifest['project_directory']
 assert manifest['iterations']==5000 and manifest['configured_cpu_hz']==82000000
 for n,h in manifest['input_sha256'].items():assert sha(ROOT/n)==h,'Input changed: '+n
 cp=json.loads((project/'checkpoints/clock82_checkpoint.json').read_text())
 for n,h in cp['checkpoint_sha256'].items():assert sha(project/'checkpoints'/n)==h,n
 if a.verify_only:
  bit=ROOT/manifest['bitstream'];assert sha(bit)==manifest['bitstream_sha256'];print('PASS board5000 source, image, checkpoint and SRAM bitstream hashes');return
 out=ROOT/'simulation/results/board5000_build';out.mkdir(parents=True,exist_ok=True)
 env=os.environ.copy();env['PYTHONUTF8']='1'
 with (out/'native_build.log').open('wb') as stream:
  def native(name):subprocess.run([str(a.pds_home/'bin/pds_shell.exe'),'-f',name],cwd=project,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=3600)
  native('rebuild_stage.tcl')
  subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools/verify_clock82_checkpoint.py'),'--project',str(project),'--install'],env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
  native('pnr_stage.tcl')
  text=(project/'report_timing/top.rtr').read_text(errors='replace')
  assert 'All Constraints Met.' in text,'Timing failed; bitstream not generated'
  m=re.search(r'(\d+\.\d+) MHz\s+(\d+\.\d+) MHz',text);assert m and abs(float(m[1])-82)<.01
  for name in ('Setup Summary(Slow Corner)','Hold Summary(Slow Corner)','Setup Summary(Fast Corner)','Hold Summary(Fast Corner)'):
   block=text.split(name+':',1)[1].split('====',1)[0];v=re.search(r'\n\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(\d+)\s+(\d+)',block);assert v and float(v[1])>=0 and int(v[3])==0,name
  # generate_bitstream.tcl uses the documented -force_to_run option with
  # an explicit routed DB, only after this driver accepts its timing report.
  native('generate_bitstream.tcl')
 bit=project/'generate_bitstream/top.sbit';assert bit.is_file() and bit.stat().st_size>1000
 assert sha(project/'device_map/top_map.adf')==cp['checkpoint_sha256']['clock82_map.adf']
 for n,h in manifest['input_sha256'].items():assert sha(ROOT/n)==h,'Input changed during build: '+n
 dest=ROOT/manifest['bitstream'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(bit,dest)
 result=dict(status='PASS',scope='Native5000 image rebuild and bitstream generation; no board programming',bitstream=str(dest.relative_to(ROOT)),bitstream_sha256=sha(dest),configured_cpu_hz=82000000,iterations=5000,estimated_fmax_mhz=float(m[2]),timing_sha256=sha(project/'report_timing/top.rtr'))
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS board5000 native build and bitstream',dest)
if __name__=='__main__':main()
