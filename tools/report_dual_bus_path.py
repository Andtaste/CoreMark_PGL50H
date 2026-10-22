"""Read existing routed ADIF; report only FIFO-read-pointer to IF RAM CE paths."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from archive_dual_issue import paths
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_ram_logic','dual_bus_split','dual_bus_local'),required=True);a=ap.parse_args()
 source=ROOT/('simulation/results/load_bp_'+a.variant);adf=source/'pds/place_route/top_pnr.adf'
 dest=ROOT/'simulation/results/dual_bus_paths'/a.variant;dest.mkdir(parents=True,exist_ok=True)
 guard={p:sha(p) for p in (adf,source/'pds/report_timing/top.rtr',ROOT/'docs/accepted_baseline.json',ROOT/'hardware/pds/report_timing/top.rtr')}
 command='report_timing -input_db_file {'+adf.as_posix()+'} -max_path 30 -nworst 1 -from {soc/cpu/memory_queue/rd*/CLK} -to {soc/bus/ram_*/U_ipml_dpram_*/ADDR_LOOP*.DATA_LOOP*.U_GTP_DRM18K/iGopDrm_inv/CEA*}'
 tcl=dest/'target.tcl';tcl.write_text('set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\n'+command+'\n')
 with (dest/'build.log').open('wb') as f:p=subprocess.run([r'E:\pango\PDS_2022.2-SP1-Lite\bin\pds_shell.exe','-f',str(tcl)],cwd=dest,stdout=f,stderr=subprocess.STDOUT,timeout=180)
 log=(dest/'build.log').read_text(errors='replace');assert p.returncode==0 and 'not a valid startpoint' not in log,log[-3000:]
 report=dest/'report_timing/top.rtr';timing=paths(report);assert timing and all('/memory_queue/rd' in t['start'] and '/CEA' in t['end'] for t in timing),timing
 for q,h in guard.items():assert sha(q)==h,q
 x=dict(status='PASS',variant=a.variant,scope='Timing report only; existing routed design, no synthesis/placement/routing rerun',slow_setup_paths=timing,
  input_sha256={str(q.relative_to(ROOT)):sha(q) for q in (adf,tcl,Path(__file__).resolve())},report_sha256=sha(report))
 (dest/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(dict(variant=a.variant,worst=timing[0]),indent=2))
if __name__=='__main__':main()
