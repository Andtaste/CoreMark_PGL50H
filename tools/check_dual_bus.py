"""Compare bus ports, RAM enables and observable state cycle by cycle."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_bus_split','dual_bus_local'),required=True);a=ap.parse_args()
 out=ROOT/('simulation/results/load_bp_'+a.variant);dest=out/'bus_equivalence';dest.mkdir(exist_ok=True)
 original=ROOT/'simulation/results/load_bp_dual_ram_logic/nc_local_bus.v';reference=dest/'bus_reference.v';reference.write_text(original.read_text().replace('module nc_local_bus #','module bus_reference #'))
 files=[reference,out/'nc_local_bus.v',ROOT/'hardware/pds/source/perips/nc_uart.v',out/'pango_ram_wide_models.v',ROOT/'simulation/research/dual_ram/bus_equivalence_tb.v']
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe'
 def run(cmd,name):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(dest/name).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(name,(p.stdout+p.stderr)[-3000:]);return p.stdout.decode(errors='replace')
 run([iv,'-g2012','-s','bus_equivalence_tb','-o',dest/'bus.vvp',*files],'compile.log')
 t=run([iv.with_name('vvp.exe'),dest/'bus.vvp'],'simulation.log');assert 'PASS bus cycle equivalence checks=200000' in t,t
 # The unchanged registered credit prevents bus ready from reaching EX/ID.
 core=(out/'nc_core.v').read_text();fifo=ROOT/'hardware/pds/source/core/nc_fifo.v'
 assert 'wire ex_fire=execute_valid && mem_credit;' in core and 'assign in_ready=count!=DEPTH;' in fifo.read_text()
 inputs=files+[original,fifo,out/'nc_core.v',Path(__file__).resolve()]
 x=dict(status='PASS',variant=a.variant,tests=[t.strip(),'PASS registered FIFO credit and EX boundary unchanged'],input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs})
 (dest/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(t.strip())
if __name__=='__main__':main()
