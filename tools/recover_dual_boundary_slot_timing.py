"""Complete read-only STA after the original flow timed out after PNR finished."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/load_bp_dual_boundary_slot';work=src/'pds';adf=work/'place_route/top_pnr.adf';h=sha(adf);assert 'Total CPU time to pnr completion' in (work/'place_route/top.prr').read_text(errors='replace')
 out=src/'recovered_sta';out.mkdir(exist_ok=True);tcl=out/'run.tcl';tcl.write_text('set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\nreport_timing -force_to_run -input_db_file {'+adf.as_posix()+'} -max_path 30 -nworst 1\n')
 with (out/'build.log').open('wb') as f:p=subprocess.run([r'E:\pango\PDS_2022.2-SP1-Lite\bin\pds_shell.exe','-f',str(tcl)],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=240)
 assert p.returncode==0 and sha(adf)==h;report=out/'report_timing/top.rtr';text=report.read_text(errors='replace');resource=(work/'device_map/top.dmr').read_text(errors='replace');corners={}
 for name in ('Setup Summary(Slow Corner)','Hold Summary(Slow Corner)','Setup Summary(Fast Corner)','Hold Summary(Fast Corner)'):
  b=text.split(name+':',1)[1].split('====',1)[0];s=re.search(r'\n\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(\d+)\s+(\d+)',b);assert s;corners[name]=dict(worst_slack_ns=float(s[1]),failing_endpoints=int(s[3]))
 row=re.search(r'(\d+\.\d+) MHz\s+(\d+\.\d+) MHz',text);assert row
 import shutil
 shutil.copyfile(report,work/'report_timing/top.rtr')
 g=json.loads((src/'generation.json').read_text());inputs=[src/Path(n).name for n in g['override_sha256']]+[adf,report,work/'device_map/top.dmr',work/'run.tcl',tcl,Path(__file__).resolve()]
 for n,v in g['override_sha256'].items():assert sha(src/Path(n).name)==v
 x=dict(status='PASS' if 'All Constraints Met.' in text else 'TIMING_FAILED',variant='dual_boundary_slot',flow_status='PDS_TIMEOUT_DURING_STA_AFTER_PNR_COMPLETED',pds_exit_code=None,sta_exit_code=0,estimated_fmax_mhz=float(row[2]),corners=corners,resources={k:int(re.search(r'\| '+re.escape(k)+r'\s+\|\s+(\d+)',resource)[1]) for k in ('LUT','FF','Distributed RAM','DRM','APM')},tcl_sha256=sha(work/'run.tcl'),input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs},scope='PNR completed once. Original 900s flow timed out while loading the routed database for STA. This read-only report uses exactly that database; no reroute, seed change or timing-constraint change.')
 (work/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({k:v for k,v in x.items() if k!='input_sha256'},indent=2))
if __name__=='__main__':main()
