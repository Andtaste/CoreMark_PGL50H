"""Validate generated vendor RAM contents and actual-top UART/reset configuration."""
from pathlib import Path
import hashlib,json,subprocess,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 project=ROOT/'hardware/pds_board5000';out=ROOT/'simulation/results/board5000_io';out.mkdir(exist_ok=True)
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe');inputs=[];tests=[]
 def run(cmd,label):
  x=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(out/(label+'.log')).write_bytes(x.stdout+x.stderr);assert x.returncode==0,(label,(x.stdout+x.stderr)[-3000:]);return x.stdout.decode(errors='replace')
 folder=project/'ipcore/ram1_tdp';vendor=Path('E:/pango/PDS_2022.2-SP1-Lite/arch/vendor/pango/verilog/simulation/GTP_DRM18K.v')
 sources=[folder/'ram1_tdp.v',folder/'rtl/ipml_dpram_v1_6_ram1_tdp.v',vendor,ROOT/'simulation/research/dual_ram/wide_ip_tb.v'];inputs+=sources+[folder/'rtl/ram1_tdp_init_param.v',project/'memory/boot.hex',project/'memory/boot_interleaved.hex']
 run([iv,'-g2012','-s','wide_ip_tb','-I',folder/'rtl','-o',out/'ram.vvp',*sources],'ram_compile')
 t=run([vvp,out/'ram.vvp','+image='+str(project/'memory/boot.hex')],'ram');assert 'PASS generated A64/B32 IP initialization/bytewrites/coherence' in t;tests.append(t.strip())
 tb=out/'uart82_tb.v';shutil.copyfile(ROOT/'simulation/tb/uart82_tb.v',tb)
 actual=[p for d in ('core','perips','sys_bus','top','source') for p in sorted((project/'source'/d).glob('*.v'))]
 model=ROOT/'simulation/models/pango_ram_wide_models.v';inputs+=[*actual,model,tb]
 run([iv,'-g2012','-s','uart82_tb','-o',out/'uart.vvp',*actual,model,tb],'uart_compile')
 t=run([vvp,out/'uart.vvp'],'uart');assert 'PASS actual top CLOCK_HZ82000000 DIV712 A5 exact-cycle 8N1' in t;tests.append(t.strip())
 record=dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):sha(p) for p in inputs},scope='All16384 actual vendor-initialized RV32 words checked, both ports and byte writes; real top/reset/UART DIV712 checked. No physical board measurement.')
 (ROOT/'docs/board5000_20261022/io_result.json').write_text(json.dumps(record,indent=2)+'\n');print('\n'.join(tests))
if __name__=='__main__':main()
