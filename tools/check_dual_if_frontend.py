"""Compare complete old/new frontends under arbitrary response bits and control."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_if_class','dual_if_parts'),required=True);a=ap.parse_args()
 out=ROOT/('simulation/results/load_bp_'+a.variant);dest=out/'frontend_equivalence';dest.mkdir(exist_ok=True)
 original=ROOT/'simulation/results/load_bp_dual_ram_logic/nc_fetch.v';reference=dest/'fetch_reference.v'
 reference.write_text(original.read_text().replace('module nc_fetch #','module fetch_reference #'))
 tb=ROOT/'simulation/research/dual_ram/if_class_equivalence_tb.v';files=[reference,out/'nc_fetch.v',out/'nc_btb.v',tb]
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe'
 def run(cmd,name):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(dest/name).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(name,(p.stdout+p.stderr)[-3000:]);return p.stdout.decode(errors='replace')
 run([iv,'-g2012','-s','if_class_equivalence_tb','-o',dest/'sim.vvp',*files],'compile.log')
 t=run([iv.with_name('vvp.exe'),dest/'sim.vvp'],'simulation.log');assert 'PASS frontend cycle equivalence checks=200000' in t,t
 x=dict(status='PASS',variant=a.variant,tests=[t.strip()],scope='Arbitrary response/control stimulus, including unsolicited responses; real protocol/ownership also covered by inherited frontend unit and SoC tests',
  input_sha256={str(p.relative_to(ROOT)):sha(p) for p in files+[original,Path(__file__).resolve()]})
 (dest/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(t.strip())
if __name__=='__main__':main()
