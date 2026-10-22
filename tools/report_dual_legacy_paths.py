"""Read-only timing around the word FIFO, returned loads and both ALU lanes."""
from pathlib import Path
import argparse,json,hashlib,re,subprocess
from parse_dual_joint_timing import paths
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();assert re.fullmatch(r'dual_legacy_[a-z_]+',a.variant)
 src=ROOT/('simulation/results/load_bp_'+a.variant);adf=src/'pds/place_route/top_pnr.adf';out=src/'targeted_paths';out.mkdir(exist_ok=True)
 guard={p:sha(p) for p in (adf,src/'pds/report_timing/top.rtr',ROOT/'docs/accepted_baseline.json',ROOT/'docs/accepted_dual_baseline.json',ROOT/'hardware/pds/report_timing/top.rtr')}
 common='report_timing -force_to_run -input_db_file {'+adf.as_posix()+'} -max_path 30 -nworst 1'
 cmds={
 'front_feedback':' -from {soc/cpu/fetch/head_*/CLK} -to {soc/cpu/fetch/head_* soc/cpu/fetch/rd* soc/cpu/fetch/count*}',
 'return_data':' -from {soc/bus/ram_code/*/CLKB* soc/bus/ram_data/*/CLKB*}',
 'operand_ready':' -from {soc/cpu/operands/dep_*/CLK soc/cpu/operands/w*/CLK}',
 'mul_enable':' -to {soc/cpu/multiply/*/CE_X soc/cpu/multiply/*/CE_Y}',
 'redirect':' -to {soc/cpu/redirect* soc/cpu/branch_redirect*}'}
 tcl=out/'run.tcl';tcl.write_text('set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\n'+''.join(common+opts+'\nfile copy -force report_timing/top.rtr '+k+'.rtr\n' for k,opts in cmds.items()))
 with (out/'build.log').open('wb') as f:p=subprocess.run([r'E:\pango\PDS_2022.2-SP1-Lite\bin\pds_shell.exe','-f',str(tcl)],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=360)
 assert p.returncode==0;reports={}
 for k in cmds:
  q=out/(k+'.rtr');parts=q.read_text(errors='replace').split('Startpoint  : ')[1:31]
  reports[k]=[x for x,part in zip(paths(q),parts) if re.search(r'Path Type\s*:\s*max \(slow corner\)',part)];assert reports[k],k
 for p,h in guard.items():assert sha(p)==h,p
 x=dict(status='PASS',scope='PASS means reports collected, not timing closure',paths=reports,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in (adf,tcl,Path(__file__).resolve())},report_sha256={k+'.rtr':sha(out/(k+'.rtr')) for k in cmds});(out/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({k:v[0] for k,v in reports.items()},indent=2))
if __name__=='__main__':main()
