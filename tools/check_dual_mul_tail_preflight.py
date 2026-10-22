"""Reproduce and identify the legacy monitor's missing lane qualification."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/load_bp_dual_boundary_multail';out=src/'monitor_preflight';original=out/'legacy_soc_tb.v';tb=out/'diagnostic_soc_tb.v';s=original.read_text();old='$fatal(1,"MUL/WB duplicate tag has different values");';assert s.count(old)==1;s=s.replace(old,'''begin $display("LANE_DIAG lane=%0d tag=%0d wtag=%0d m=%08x w0=%08x w1=%08x commit1=%0d",dut.cpu.m_lane,dut.cpu.m_tag,dut.cpu.w_tag,dut.cpu.m_data,dut.cpu.w_result,dut.cpu.w1_result,dut.cpu.commit1);$fatal(1,"MUL/WB duplicate tag has different values");end''');tb.write_text(s);g=json.loads((src/'generation.json').read_text());files=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[]);files=[src/p.name if str(p.relative_to(ROOT)) in g['override_sha256'] else p for p in files]+[src/'pango_ram_wide_models.v'];iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe');image=ROOT/'simulation/results/random_17.hex'
 x=subprocess.run(list(map(str,[iv,'-g2012','-s','soc_tb','-o',out/'diag.vvp',*files,tb])),cwd=ROOT,capture_output=True,timeout=120);(out/'compile.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0
 x=subprocess.run(list(map(str,[vvp,out/'diag.vvp',f'+image={image}',f'+trace={out}/diagnostic.trace',f'+uart={out}/unused_uart.txt'])),cwd=ROOT,capture_output=True,timeout=120);(out/'diagnostic.log').write_bytes(x.stdout+x.stderr);t=x.stdout.decode(errors='replace');m=re.search(r'LANE_DIAG lane=(\d+) tag=(\d+) wtag=(\d+) m=([0-9a-f]+) w0=([0-9a-f]+) w1=([0-9a-f]+) commit1=(\d+)',t);assert 'FATAL:' in t and m,t
 assert m[1]=='1' and m[2]==m[3] and m[4]!=m[5] and m[4]==m[6] and m[7]=='1',m.groups()
 inputs=[Path(__file__).resolve(),original,tb,image,*files];(out/'result.json').write_text(json.dumps(dict(status='PASS',scope='Diagnostic replay expected old assertion failure; lane1 MUL equals W1 while different from unrelated W0. Candidate RTL unchanged; corrected monitors also assert both lanes.',tests=[m[0]],input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print(m[0])
if __name__=='__main__':main()
