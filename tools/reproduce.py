from pathlib import Path
import argparse,json,os,shutil,subprocess,sys
R=Path(__file__).resolve().parents[1]
os.environ["PYTHONUTF8"]="1"
def run(args,**kw):subprocess.run(list(map(str,args)),check=True,**kw)
def main():
 p=argparse.ArgumentParser();p.add_argument('task',choices=['coremark','ip']);p.add_argument('--project',choices=['pds'],default='pds');p.add_argument('--pds-home');a=p.parse_args()
 if a.task=='coremark':
  m=json.loads((R/'reproduction/coremark_profile.json').read_text());cmd=[sys.executable,R/'tools/build_coremark.py','--iterations',m['iterations'],'--cpu-hz',m['configured_cpu_hz'],'--profile',m['profile'],'--stack-offset',m['stack_offset'],'--source-date-epoch',m['source_date_epoch'],'--tag','reproduce']
  cmd+=['--extra-cflag='+v for v in m['extra_cflags']]
  cmd+=['--module-cflag='+n+':'+v for n,vs in m['module_cflags'].items() for v in vs]
  run(cmd);b=R/'sw/build'/('coremark_performance_'+str(m['iterations'])+'_reproduce/coremark.bin');data=b.read_bytes().ljust(65536,b'\0');mem=R/'hardware/pds/memory'
  for width,name in [(4,'boot.hex'),(8,'boot64.dat')]:
   (mem/name).write_text(''.join(data[i:i+width][::-1].hex()+'\n' for i in range(0,len(data),width)))
  print('CoreMark firmware installed in hardware/pds/memory. Regenerate RAM IP next.');return
 home=a.pds_home or os.environ.get('PDS_HOME');exe=Path(home)/'bin/ip_generate.exe' if home else Path(shutil.which('ip_generate.exe') or '')
 if not exe.is_file():raise SystemExit('Set PDS_HOME or --pds-home to the PDS 2025.2 installation directory')
 run([sys.executable,R/'prepare_paths.py']);project=R/'hardware'/a.project
 for name in (['ram1_tdp','ram2_tdp'] if a.project=='pds' else ['ram1_tdp','ram2_tdp','ram3_tdp']):
  f=project/'ipcore'/name/(name+'.idf');run([exe,'-i',f,'-disable-syn'],cwd=f.parent)
 print('RAM IP regenerated. Rebuild the supplied PDS project from Compile.')
if __name__=='__main__':main()
