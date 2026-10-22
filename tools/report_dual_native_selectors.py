"""Read-only routed timing for both sides of the new selector-register boundary."""
from pathlib import Path
import hashlib,json,re,subprocess
from archive_dual_issue import paths
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/load_bp_dual_native_both';adf=src/'pds/place_route/top_pnr.adf'
 dest=ROOT/'simulation/results/dual_native_selectors';dest.mkdir(exist_ok=True)
 guard={p:sha(p) for p in (adf,src/'pds/report_timing/top.rtr',ROOT/'docs/accepted_dual_baseline.json',ROOT/'docs/accepted_baseline.json',ROOT/'hardware/pds/report_timing/top.rtr')}
 pins=' '.join('soc/cpu/operands/'+prefix+'_*' for prefix in ('sf','sf1','sm','sw','sw1'))
 clocks=' '.join(p+'/CLK' for p in pins.split())
 common='report_timing -force_to_run -input_db_file {'+adf.as_posix()+'} -max_path 30 -nworst 1'
 tcl=dest/'run.tcl';tcl.write_text('set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\n'+common+' -to {'+pins+'}\nfile copy -force report_timing/top.rtr into_selectors.rtr\n'+common+' -from {'+clocks+'}\nfile copy -force report_timing/top.rtr from_selectors.rtr\n')
 with (dest/'build.log').open('wb') as f:p=subprocess.run([r'E:\pango\PDS_2022.2-SP1-Lite\bin\pds_shell.exe','-f',str(tcl)],cwd=dest,stdout=f,stderr=subprocess.STDOUT,timeout=180)
 assert p.returncode==0
 reports={}
 for k in ('into_selectors','from_selectors'):
  report=dest/(k+'.rtr');parts=report.read_text(errors='replace').split('Startpoint  : ')[1:31]
  reports[k]=[x for x,part in zip(paths(report),parts) if re.search(r'Path Type\s*:\s*max \(slow corner\)',part)]
  assert reports[k],k
 for p,h in guard.items():assert sha(p)==h,p
 (dest/'result.json').write_text(json.dumps(dict(status='PASS',paths=reports,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in (adf,tcl,Path(__file__).resolve())},report_sha256={k+'.rtr':sha(dest/(k+'.rtr')) for k in reports}),indent=2)+'\n')
 print(json.dumps({k:v[0] for k,v in reports.items()},indent=2))
if __name__=='__main__':main()
