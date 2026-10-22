"""Actual bus/MEM equivalence and real-SoC write publication checks."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);ap.add_argument('--mode',choices=('proof','soc'),required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant)
 if a.mode=='soc':
  base=ROOT/'tools/check_dual_store_mmio_v2.py';s=base.read_text().replace('dual_boundary_storemmio',a.variant)
  old=".replace('posted_count==0 || posted_count!=drain_count','posted_count!=drain_count')";assert s.count(old)==1
  s=s.replace(old,old+'''.replace('  was_local=dut.bus.da_fire', '  if(dut.bus.dwrite && (!dut.bus.dv || dut.bus.wa!==dut.bus.da)) $fatal(1,"Published write valid/address contract");\\n  was_local=dut.bus.da_fire')''')
  ns={'__file__':str(base),'__name__':'simple_soc'};exec(compile(s,str(base),'exec'),ns);ns['main']();p=src/'posted_soc_final/result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__));x['scope']+='; published write implies valid and held write address equals selected address every cycle';p.write_text(json.dumps(x,indent=2)+'\n');return
 out=src/'simple_proof';out.mkdir(exist_ok=True);ref=ROOT/'simulation/results/load_bp_dual_boundary_storeack';inputs=[Path(__file__).resolve()];tests=[]
 def linux(p):return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
 def run(script,name):
  p=subprocess.run(['wsl.exe','-d','Ubuntu','--','yosys','-p',script],cwd=ROOT,capture_output=True,timeout=180);(out/(name+'.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(name,(p.stdout+p.stderr)[-3000:])
 # Observe every bus state bit, so temporal induction also checks hidden state.
 generated=[]
 for folder,label in ((ref,'gold'),(src,'gate')):
  p=folder/'nc_local_bus.v';s=p.read_text().replace('module nc_local_bus #','module '+label+'_bus #').replace('output reg[31:0] tohost);','output reg[31:0] tohost,output wire[200:0] equivalence_state);');assert 'equivalence_state);' in s
  s=s.replace('endmodule','assign equivalence_state={ipending,ibank,ierror,dpending,dbank,dis_ram,derror,mmio_data,mtime,mtimecmp,gpio,tohost};\nendmodule');f=out/(label+'_bus.v');f.write_text(s);generated.append(f);inputs +=[p,f]
 stub=out/'stubs.v';stub.write_text('''module nc_uart #(parameter CLOCK_HZ=75000000)(input clk,rst_n,send,input[7:0] data,output ready,tx);assign ready=1'b1;assign tx=1'b1;endmodule
 module ram1_tdp(input a_clk,a_rst,a_clk_en,input[12:0] a_addr,input[63:0] a_wr_data,input a_wr_en,input[7:0] a_wr_byte_en,output[63:0] a_rd_data,input b_clk,b_rst,b_clk_en,input[13:0] b_addr,input[31:0] b_wr_data,input b_wr_en,input[3:0] b_wr_byte_en,output[31:0] b_rd_data);assign a_rd_data=64'b0;assign b_rd_data=32'b0;endmodule
 module ram2_tdp(input a_clk,a_rst,a_clk_en,input[11:0] a_addr,input[63:0] a_wr_data,input a_wr_en,input[7:0] a_wr_byte_en,output[63:0] a_rd_data,input b_clk,b_rst,b_clk_en,input[12:0] b_addr,input[31:0] b_wr_data,input b_wr_en,input[3:0] b_wr_byte_en,output[31:0] b_rd_data);assign a_rd_data=64'b0;assign b_rd_data=32'b0;endmodule
 ''');inputs.append(stub)
 wrapper=out/'bus_miter.v';common='input clk,rst_n,iv,ior,dv_in,dor,dwrite,input[31:0] ia,da,dw,wa_in,input[3:0] dm'
 # The wrapper encodes the actual core publication contract, not an assumption
 # that arbitrary standalone buses allow writes without valid or differing addr.
 s='module bus_miter('+common+',output equal);wire dv=dv_in|dwrite;wire[31:0] wa=dwrite?da:wa_in;\n'
 for label in ('gold','gate'):
  s+='wire[305:0] '+label+'_out;\n'+label+'_bus b_'+label+'(.clk(clk),.rst_n(rst_n),.iv(iv),.ir('+label+'_out[0]),.ia(ia),.iov('+label+'_out[1]),.ior(ior),.idata('+label+'_out[65:2]),.ierr('+label+'_out[66]),.dv(dv),.dr('+label+'_out[67]),.da(da),.dw(dw),.wa(wa),.dm(dm),.dwrite(dwrite),.dov('+label+'_out[68]),.dor(dor),.ddata('+label+'_out[100:69]),.derr('+label+'_out[101]),.uart_tx('+label+'_out[102]),.timer_irq('+label+'_out[103]),.gpio_out(),.tohost(),.equivalence_state('+label+'_out[304:104]));assign '+label+'_out[305]=1\'b0;\n'
 s+='assign equal=gold_out==gate_out;endmodule\n';wrapper.write_text(s);inputs.append(wrapper)
 files=' '.join(linux(p) for p in [*generated,stub,wrapper]);run('read_verilog -sv '+files+'; prep -top bus_miter -flatten; async2sync; opt; sat -verify -seq 2 -tempinduct -set-init-zero -prove equal 1','bus_equivalence');tests.append('PASS actual bus RTL all internal state/output equivalence by temporal induction under core write publication contract; RAM/UART stubbed, separate integration tests cover them')
 if a.variant.endswith('storelogic'):
  for folder,label in ((ref,'gold'),(src,'gate')):
   p=folder/'nc_memory.v';f=out/(label+'_mem.v');f.write_text(p.read_text().replace('module nc_memory #','module '+label+'_mem #'));inputs +=[p,f]
  files=' '.join(linux(out/(label+'_mem.v')) for label in ('gold','gate'))
  # Check both the posted-enabled SoC case and the default generic fallback.
  for mode in (0,1):
   run('read_verilog -sv '+files+f'; chparam -set EARLY_REQUEST 1 -set POST_LOCAL_STORES {mode} gold_mem; chparam -set EARLY_REQUEST 1 -set POST_LOCAL_STORES {mode} gate_mem; proc; memory; equiv_make gold_mem gate_mem equiv; hierarchy -top equiv; equiv_simple; equiv_induct -seq 2; equiv_status -assert','memory_equivalence_'+str(mode));tests.append('PASS actual full MEM sequential equivalence POST_LOCAL_STORES='+str(mode))
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print(a.variant,'proof PASS',len(tests))
if __name__=='__main__':main()
