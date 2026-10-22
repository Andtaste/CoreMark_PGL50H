"""Read-only RAM enable and registered operand-source path comparisons."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from parse_dual_joint_timing import paths
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);out=src/'bank_paths';out.mkdir(exist_ok=True);adf=src/'pds/place_route/top_pnr.adf';guard={p:sha(p) for p in (adf,src/'pds/report_timing/top.rtr',ROOT/'docs/accepted_dual_baseline.json',ROOT/'hardware/pds/report_timing/top.rtr')}
 ram=' -to {soc/bus/ram_code/*/CEB* soc/bus/ram_data/*/CEB*}'
 queries={'ram_enable':ram,'registered_operand_match':' -from {soc/cpu/operands/sm_a*/*/CLK}'+ram,'memory_to_ram':' -from {soc/cpu/memory/*}'+ram,'mmio_write':' -to {soc/bus/tohost*/* soc/bus/gpio*/* soc/bus/mtimecmp*/*}'}
 tcl=out/'run.tcl';common='report_timing -force_to_run -input_db_file {'+adf.as_posix()+'} -max_path 5 -nworst 1';tcl.write_text('set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\n'+''.join(common+q+'\nfile copy -force report_timing/top.rtr '+n+'.rtr\n' for n,q in queries.items()))
 with (out/'build.log').open('wb') as f:x=subprocess.run([r'E:\pango\PDS_2022.2-SP1-Lite\bin\pds_shell.exe','-f',str(tcl)],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=600)
 assert x.returncode==0;reports={n:paths(out/(n+'.rtr'))[:5] for n in queries}
 for n,z in reports.items():assert z,n
 for p,h in guard.items():assert sha(p)==h,p
 inputs=[adf,tcl,Path(__file__).resolve(),ROOT/'tools/parse_dual_joint_timing.py'];(out/'result.json').write_text(json.dumps(dict(status='PASS',scope='Read-only routed snapshot, no timing-pass claim',paths=reports,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs},report_sha256={n+'.rtr':sha(out/(n+'.rtr')) for n in queries}),indent=2)+'\n');print(json.dumps({n:z[0] for n,z in reports.items()},indent=2))
if __name__=='__main__':main()
