"""Use verified Pango DRM pin names and reject unmatched RAM endpoint queries."""
from pathlib import Path
import argparse,hashlib,json,subprocess,re
from parse_dual_joint_timing import paths
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();assert re.fullmatch('dual_lsu_[a-z]+',a.variant)
 src=ROOT/('simulation/results/load_bp_'+a.variant);out=src/'lsu_paths';out.mkdir(exist_ok=True);adf=src/'pds/place_route/top_pnr.adf'
 guard={p:sha(p) for p in (adf,src/'pds/report_timing/top.rtr',ROOT/'docs/accepted_dual_baseline.json',ROOT/'hardware/pds/report_timing/top.rtr')}
 cmd={
 'ram_address':' -to {soc/bus/ram_code/*/ADA* soc/bus/ram_code/*/ADB* soc/bus/ram_data/*/ADA* soc/bus/ram_data/*/ADB*}',
 'ram_return':' -from {soc/bus/ram_code/*/CLKA* soc/bus/ram_code/*/CLKB* soc/bus/ram_data/*/CLKA* soc/bus/ram_data/*/CLKB*}',
 'memory_to_core':' -from {soc/cpu/memory/*/CLK} -to {soc/cpu/execute/* soc/cpu/fetch/* soc/cpu/operands/*}' }
 tcl=out/'run.tcl';common='report_timing -force_to_run -input_db_file {'+adf.as_posix()+'} -max_path 30 -nworst 1'
 tcl.write_text('set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\n'+''.join(common+q+'\nfile copy -force report_timing/top.rtr '+n+'.rtr\n' for n,q in cmd.items()))
 with (out/'build.log').open('wb') as f:p=subprocess.run([r'E:\pango\PDS_2022.2-SP1-Lite\bin\pds_shell.exe','-f',str(tcl)],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=360)
 assert p.returncode==0;reports={}
 for n in cmd:
  q=out/(n+'.rtr');parts=q.read_text(errors='replace').split('Startpoint  : ')[1:31];reports[n]=[x for x,b in zip(paths(q),parts) if 'Path Type   : max (slow corner)' in b];assert reports[n],n
 assert all('/ram_' in x['end'] and re.search('/AD[AB]',x['end']) for x in reports['ram_address'])
 assert all('/ram_' in x['start'] for x in reports['ram_return'])
 assert all('/cpu/memory/' in x['start'] for x in reports['memory_to_core'])
 for p,h in guard.items():assert sha(p)==h,p
 x=dict(status='PASS',scope='Timing evidence collection; no implication that timing is closed',paths=reports,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in (adf,tcl,Path(__file__).resolve())},report_sha256={n+'.rtr':sha(out/(n+'.rtr')) for n in cmd})
 (out/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(a.variant,json.dumps({n:v[0] for n,v in reports.items()}))
if __name__=='__main__':main()
