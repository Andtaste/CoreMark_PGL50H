"""Build the ordinary PDS project; require actual routed board pins AND all-corner timing."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess,sys
from verify_board_pnr import inspect
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--verify-only',action='store_true');p.add_argument('--pds-home',type=Path,default=Path(os.environ.get('PDS_HOME','E:/pango/PDS_2022.2-SP1-Lite')));a=p.parse_args()
 manifest=json.loads((ROOT/'docs/board5000_20261022/board_manifest.json').read_text());project=ROOT/manifest['project_directory']
 assert manifest['iterations']==5000 and manifest['configured_cpu_hz']==82000000
 for n,h in manifest['input_sha256'].items():assert sha(ROOT/n)==h,'Input changed: '+n
 pds=project/'new_core.pds';data=pds.read_text()
 assert 'constraints/board.fdc' in data and 'input_place_db_file' not in data
 for option,key in (('gplace_seed','chosen_place_seed'),('groute_seed','chosen_route_seed')):
  match=re.search(r'\(_option '+option+r' \(_integer (\d+)\)\)',data)
  assert (int(match[1]) if match else 0)==manifest[key],option
 if a.verify_only:
  bit=ROOT/manifest['bitstream'];assert sha(bit)==manifest['bitstream_sha256'];print('PASS board5000 source, configuration and SRAM bitstream hashes');return
 # Run exactly the normal GUI project flow from RTL, without importing a checkpoint.
 data=re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',data);pds.write_bytes(data.encode())
 out=ROOT/'simulation/results/board5000_build';out.mkdir(parents=True,exist_ok=True)
 env=os.environ.copy();env['PYTHONUTF8']='1'
 with (out/'native_build.log').open('wb') as stream:
  def native(arguments):subprocess.run([str(a.pds_home/'bin/pds_shell.exe'),*arguments],cwd=project,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=3600)
  native(['-project','new_core.pds','-run','report_timing'])
  result=inspect(project)
  for n,h in manifest['input_sha256'].items():assert sha(ROOT/n)==h,'Input changed: '+n
  # generate_bitstream.tcl uses the documented -force_to_run option with
  # an explicit routed DB, only after this driver accepts its timing report.
  native(['-f','generate_bitstream.tcl'])
 bit=project/'generate_bitstream/top.sbit';assert bit.is_file() and bit.stat().st_size>1000
 for n,h in manifest['input_sha256'].items():assert sha(ROOT/n)==h,'Input changed during build: '+n
 dest=ROOT/manifest['bitstream'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(bit,dest)
 result.update(scope='Native ordinary PDS project build; actual routed board pins and all-corner timing verified; no board programming',bitstream=str(dest.relative_to(ROOT)),bitstream_sha256=sha(dest),configured_cpu_hz=82000000,iterations=5000)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS board5000 native build and bitstream',dest)
if __name__=='__main__':main()
