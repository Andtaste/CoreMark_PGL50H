"""Collect completed immutable STA reports, including negative-slack diagnostics."""
from pathlib import Path
import argparse,json,hashlib,re
from parse_dual_joint_timing import paths
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();out=ROOT/'simulation/results/dual_joint_paths'/a.variant;src=ROOT/('simulation/results/load_bp_'+a.variant)
 reports={};names=['frontend','front_feedback','wb_to_f1','mul_enable','redirect','side_ready']
 if a.variant=='dual_joint_reg':names+=['selector_input','selector_output']
 for name in names:
  p=out/(name+'.rtr');parts=p.read_text(errors='replace').split('Startpoint  : ')[1:31];reports[name]=[x for x,part in zip(paths(p),parts) if re.search(r'Path Type\s*:\s*max \(slow corner\)',part)];assert reports[name],name
 inputs=[src/'pds/place_route/top_pnr.adf',out/'run.tcl',Path(__file__).resolve(),ROOT/'tools/parse_dual_joint_timing.py']
 x=dict(status='PASS',variant=a.variant,scope='Read-only STA report collection; PASS means evidence parsed, not timing closure',paths=reports,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs},report_sha256={name+'.rtr':sha(out/(name+'.rtr')) for name in names})
 (out/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({k:v[0] for k,v in reports.items()},indent=2))
if __name__=='__main__':main()
