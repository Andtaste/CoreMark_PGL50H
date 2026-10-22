"""FIFO latency/credit/data equivalence against old FIFO and independent scoreboard."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_fan_guide','dual_fan_banks'),required=True);a=ap.parse_args()
 out=ROOT/('simulation/results/load_bp_'+a.variant);dest=out/'fifo_equivalence';dest.mkdir(exist_ok=True)
 original=ROOT/'hardware/pds/source/core/nc_fifo.v';ref=dest/'fifo_reference.v';ref.write_text(original.read_text().replace('module nc_fifo #','module fifo_reference #'))
 tb=ROOT/'simulation/research/dual_ram/fan_fifo_tb.v';files=[ref,out/'nc_fifo.v',tb];iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe'
 def run(cmd,name):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(dest/name).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(name,(p.stdout+p.stderr)[-3000:]);return p.stdout.decode(errors='replace')
 run([iv,'-g2012','-s','fan_fifo_tb','-o',dest/'fifo.vvp',*files],'compile.log');tests=[]
 for seed in (37,613,2026):
  t=run([iv.with_name('vvp.exe'),dest/'fifo.vvp','+seed='+str(seed)],str(seed)+'.log');assert 'PASS FIFO scoreboard' in t,t;tests.append(t.strip())
 assert 'assign in_ready=count!=DEPTH;' in (out/'nc_fifo.v').read_text()
 x=dict(status='PASS',variant=a.variant,tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in files+[original,Path(__file__).resolve()]})
 (dest/'result.json').write_text(json.dumps(x,indent=2)+'\n');print('\n'.join(tests))
if __name__=='__main__':main()
