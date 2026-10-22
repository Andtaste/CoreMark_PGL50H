"""Read-only STA of encoded dependencies to EX/MEM data and IF head consumers."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
from archive_dual_issue import paths
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);ap.add_argument('--reuse-reports',action='store_true');a=ap.parse_args()
 assert a.variant=='dual_if_parts' or re.fullmatch('dual_fwd_[a-z]+',a.variant)
 source=ROOT/('simulation/results/load_bp_'+a.variant);adf=source/'pds/place_route/top_pnr.adf'
 dest=ROOT/'simulation/results/dual_fwd_paths'/a.variant;dest.mkdir(parents=True,exist_ok=True)
 guard={p:sha(p) for p in (adf,source/'pds/report_timing/top.rtr',ROOT/'docs/accepted_baseline.json',ROOT/'hardware/pds/report_timing/top.rtr')}
 common='report_timing -force_to_run -input_db_file {'+adf.as_posix()+'} -max_path 30 -nworst 1'
 incoming=common+' -from {soc/cpu/operands/dep_*/CLK} -to {soc/cpu/memory_queue/*/WD}'
 consumer=common+' -from {soc/cpu/fetch/head_inst*/CLK soc/cpu/fetch/head_parts*/CLK}'
 writeback=common+' -from {soc/cpu/wb_q*/CLK} -to {soc/cpu/f1_valid*}'
 tcl=dest/'target.tcl';script='set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\n'+incoming+'\nfile copy -force report_timing/top.rtr dependency.rtr\n'+consumer+'\nfile copy -force report_timing/top.rtr consumer.rtr\n'+writeback+'\nfile copy -force report_timing/top.rtr writeback.rtr\n'
 previous=None
 if a.reuse_reports:
  previous=json.loads((dest/'result.json').read_text())
  for n,h in previous['input_sha256'].items():
   if Path(n).name!=Path(__file__).name:assert sha(ROOT/n)==h,n
  for n,h in previous['report_sha256'].items():assert sha(dest/n)==h,n
  assert tcl.read_text()==script
 else:
  tcl.write_text(script)
  with (dest/'build.log').open('wb') as f:p=subprocess.run([r'E:\pango\PDS_2022.2-SP1-Lite\bin\pds_shell.exe','-f',str(tcl)],cwd=dest,stdout=f,stderr=subprocess.STDOUT,timeout=240)
  log=(dest/'build.log').read_text(errors='replace');assert p.returncode==0,log[-3000:]
 def slow_paths(report):
  # Narrow endpoint sets can produce fewer than 30 setup paths; do not
  # accidentally append hold/fast paths from the remainder of the report.
  raw=paths(report);parts=report.read_text(errors='replace').split('Startpoint  : ')[1:31]
  return [x for x,part in zip(raw,parts) if re.search(r'Path Type\s*:\s*max \(slow corner\)',part)]
 reports={k:slow_paths(dest/(k+'.rtr')) for k in ('dependency','consumer','writeback')}
 assert all(reports.values()),reports
 for q,h in guard.items():assert sha(q)==h,q
 x=dict(status='PASS',variant=a.variant,scope='Existing routed ADIF read only; no rerun of implementation',paths=reports,
  input_sha256={str(q.relative_to(ROOT)):sha(q) for q in (adf,tcl,Path(__file__).resolve())},report_sha256={k+'.rtr':sha(dest/(k+'.rtr')) for k in reports})
 x['reports_reused']=a.reuse_reports
 if previous:x['previous_parser_sha256']=previous['input_sha256'][str(Path(__file__).resolve().relative_to(ROOT))]
 (dest/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(dict(variant=a.variant,worst={k:v[0] for k,v in reports.items()}),indent=2))
if __name__=='__main__':main()
