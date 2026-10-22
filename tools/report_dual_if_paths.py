"""Report RAM-to-IF classification and registered flags-to-consumer paths."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
from archive_dual_issue import paths
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args()
 assert a.variant=='dual_ram_logic' or re.fullmatch('dual_if_[a-z]+',a.variant)
 source=ROOT/('simulation/results/load_bp_'+a.variant);adf=source/'pds/place_route/top_pnr.adf'
 dest=ROOT/'simulation/results/dual_if_paths'/a.variant;dest.mkdir(parents=True,exist_ok=True)
 guard={p:sha(p) for p in (adf,source/'pds/report_timing/top.rtr',ROOT/'docs/accepted_baseline.json',ROOT/'hardware/pds/report_timing/top.rtr')}
 partial='head_parts' in (source/'nc_fetch.v').read_text()
 heads='head_parts' if partial else 'head_flags'
 common='report_timing -force_to_run -input_db_file {'+adf.as_posix()+'} -max_path 30 -nworst 1'
 incoming=common+' -from {soc/bus/ram_*/U_ipml_dpram_*/ADDR_LOOP*.DATA_LOOP*.U_GTP_DRM18K/iGopDrm_inv/CLKA*} -to {soc/cpu/fetch/flags_0* soc/cpu/fetch/flags_1* soc/cpu/fetch/flags_2* soc/cpu/fetch/flags_3* soc/cpu/fetch/'+heads+'*}'
 consumer=common+' -from {soc/cpu/fetch/'+heads+'*/CLK}'
 tcl=dest/'target.tcl';tcl.write_text('set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\n'+incoming+'\nfile copy -force report_timing/top.rtr incoming.rtr\n'+consumer+'\nfile copy -force report_timing/top.rtr consumer.rtr\n')
 with (dest/'build.log').open('wb') as f:p=subprocess.run([r'E:\pango\PDS_2022.2-SP1-Lite\bin\pds_shell.exe','-f',str(tcl)],cwd=dest,stdout=f,stderr=subprocess.STDOUT,timeout=240)
 log=(dest/'build.log').read_text(errors='replace');assert p.returncode==0,log[-3000:]
 reports={k:paths(dest/(k+'.rtr')) for k in ('incoming','consumer')}
 assert all(reports.values()),reports
 for q,h in guard.items():assert sha(q)==h,q
 x=dict(status='PASS',variant=a.variant,scope='Existing routed ADIF read only; no rerun of implementation',paths=reports,
  input_sha256={str(q.relative_to(ROOT)):sha(q) for q in (adf,tcl,Path(__file__).resolve())},report_sha256={k+'.rtr':sha(dest/(k+'.rtr')) for k in reports})
 (dest/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(dict(variant=a.variant,worst={k:v[0] for k,v in reports.items()}),indent=2))
if __name__=='__main__':main()
