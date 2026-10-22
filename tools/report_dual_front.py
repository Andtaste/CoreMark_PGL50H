"""Read-only all-head/peek register timing, including metadata and cross state."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
from archive_dual_issue import paths
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args()
 assert re.fullmatch('dual_(fwd_share|admit_[a-z]+|window_[a-z]+)',a.variant)
 src=ROOT/('simulation/results/load_bp_'+a.variant);adf=src/'pds/place_route/top_pnr.adf';out=ROOT/'simulation/results/dual_admit_front'/a.variant;out.mkdir(parents=True,exist_ok=True)
 guard={p:sha(p) for p in (adf,src/'pds/report_timing/top.rtr',ROOT/'docs/accepted_dual_baseline.json',ROOT/'docs/accepted_baseline.json',ROOT/'hardware/pds/report_timing/top.rtr')}
 tcl=out/'target.tcl';tcl.write_text('set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\nreport_timing -force_to_run -input_db_file {'+adf.as_posix()+'} -max_path 30 -nworst 1 -from {soc/cpu/fetch/head_*/CLK soc/cpu/fetch/peek_*/CLK}\nfile copy -force report_timing/top.rtr frontend.rtr\n')
 with (out/'build.log').open('wb') as f:x=subprocess.run([r'E:\pango\PDS_2022.2-SP1-Lite\bin\pds_shell.exe','-f',str(tcl)],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=240)
 assert x.returncode==0
 report=out/'frontend.rtr';raw=paths(report);parts=report.read_text(errors='replace').split('Startpoint  : ')[1:31]
 result=[x for x,p in zip(raw,parts) if re.search(r'Path Type\s*:\s*max \(slow corner\)',p)];assert result
 for p,h in guard.items():assert sha(p)==h,p
 data=dict(status='PASS',variant=a.variant,scope='all head_* and peek_* register clock pins to all endpoints, max slow corner; original routed snapshot, no PNR rerun',paths=result,
  input_sha256={str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__).resolve(),adf,tcl)},report_sha256=sha(report))
 (out/'result.json').write_text(json.dumps(data,indent=2)+'\n');print(a.variant,result[0])
if __name__=='__main__':main()
