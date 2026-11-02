from pathlib import Path
import argparse,json,os,shutil,subprocess,sys
R=Path(__file__).resolve().parents[1]
os.environ["PYTHONUTF8"]="1"
def run(args,**kw):subprocess.run(list(map(str,args)),check=True,**kw)
def main():
 p=argparse.ArgumentParser();p.add_argument('task',choices=['application','client','ip']);p.add_argument('--project',choices=['board_games'],default='board_games');p.add_argument('--pds-home');a=p.parse_args()
 if a.task=='client':run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',R/'tools/build_board_games_desktop.ps1']);return
 if a.task=='application':run([sys.executable,R/'tools/build_board_games.py','--software-only']);return
 home=a.pds_home or os.environ.get('PDS_HOME');exe=Path(home)/'bin/ip_generate.exe' if home else Path(shutil.which('ip_generate.exe') or '')
 if not exe.is_file():raise SystemExit('Set PDS_HOME or --pds-home to the PDS 2025.2 installation directory')
 run([sys.executable,R/'prepare_paths.py']);project=R/'hardware'/a.project
 for name in (['ram1_tdp','ram2_tdp'] if a.project=='pds' else ['ram1_tdp','ram2_tdp','ram3_tdp']):
  f=project/'ipcore'/name/(name+'.idf');run([exe,'-i',f,'-disable-syn'],cwd=f.parent)
 print('RAM IP regenerated. Rebuild the supplied PDS project from Compile.')
if __name__=='__main__':main()
