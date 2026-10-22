"""Read-only routed queries for ID boundaries and RAM-return-to-control paths."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from parse_dual_joint_timing import paths
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);assert (src/'pds/result.json').exists();out=src/'next_paths';out.mkdir(exist_ok=True);adf=src/'pds/place_route/top_pnr.adf';guard={p:sha(p) for p in [adf,src/'pds/report_timing/top.rtr',ROOT/'docs/accepted_dual_baseline.json',ROOT/'hardware/pds/report_timing/top.rtr']}
 ctrl=' -to {soc/cpu/redirect*/* soc/cpu/f_valid/* soc/cpu/f1_valid/* soc/bus/ram_code/*/CEB* soc/bus/ram_data/*/CEB*}'
 queries={'id_boundary':' -to {soc/cpu/fetch/* soc/cpu/operands/*}', 'operand_control':' -from {soc/cpu/operands/*}'+ctrl, 'ram_b_control':' -from {soc/bus/ram_code/*/CLKB* soc/bus/ram_data/*/CLKB*}'+ctrl}
 common='report_timing -force_to_run -input_db_file {'+adf.as_posix()+'} -max_path 5 -nworst 1';tcl=out/'run.tcl';tcl.write_text('set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\n'+''.join(common+q+'\nfile copy -force report_timing/top.rtr '+n+'.rtr\n' for n,q in queries.items()))
 with (out/'build.log').open('wb') as f:x=subprocess.run([r'E:\pango\PDS_2022.2-SP1-Lite\bin\pds_shell.exe','-f',str(tcl)],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=600)
 assert x.returncode==0
 reports={k:paths(out/(k+'.rtr'))[:5] for k in queries};assert reports['id_boundary'] and reports['operand_control']
 for p,h in guard.items():assert sha(p)==h,p
 (out/'result.json').write_text(json.dumps(dict(status='PASS',paths=reports,queries=queries,scope='Read-only routed snapshots; empty RAM-B control set is recorded as no reported matching path, not proof of whole-core noninterference',input_sha256={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__).resolve(),ROOT/'tools/parse_dual_joint_timing.py',adf,tcl]},report_sha256={k+'.rtr':sha(out/(k+'.rtr')) for k in queries}),indent=2)+'\n');print(json.dumps({k:z[:1] for k,z in reports.items()},indent=2))
if __name__=='__main__':main()
