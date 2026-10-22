"""Induct actual bus state, RAM enables, and UART send for arbitrary IP data."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);ref=ROOT/'simulation/results/load_bp_dual_boundary_storeack';out=src/'bus_induction';out.mkdir(exist_ok=True);inputs=[Path(__file__).resolve()];generated=[]
 for folder,label in ((ref,'gold'),(src,'gate')):
  p=folder/'nc_local_bus.v';s=p.read_text().replace('module nc_local_bus #','module '+label+'_bus #');s=s.replace('output reg[31:0] tohost);','output reg[31:0] tohost,input formal_uart_ready,formal_uart_tx,input[63:0] formal_iq0,formal_iq1,input[31:0] formal_dq0,formal_dq1,output[205:0] formal_state);')
  begin=s.index(' nc_uart #(');end=s.index(' assign dr=',begin);s=s[:begin]+' assign uart_ready=formal_uart_ready;assign uart_tx=formal_uart_tx;\n'+s[end:]
  begin=s.index(' ram1_tdp ram_code(');s=s[:begin]+''' assign iq0=formal_iq0;assign iq1=formal_iq1;assign dq0=formal_dq0;assign dq1=formal_dq1;
 assign formal_state={uart_send,(ia_fire && ib0 && !ia[1] && !ia[0]),(ia_fire && ib1 && !ia[1] && !ia[0]),(da_fire && db0),(da_fire && db1),ipending,ibank,ierror,dpending,dbank,dis_ram,derror,mmio_data,mtime,mtimecmp,gpio,tohost};
 endmodule
 ''';f=out/(label+'.v');f.write_text(s);inputs +=[p,f];generated.append(f)
 p=out/'miter.v';s='''module miter(input clk,rst_n,iv,ior,dv_raw,dor,dwrite,input[31:0] ia,da,dw,wa_raw,input[3:0] dm,input formal_uart_ready,formal_uart_tx,input[63:0] formal_iq0,formal_iq1,input[31:0] formal_dq0,formal_dq1,output equal);
 wire dv=dv_raw|dwrite;wire[31:0] wa=dwrite?da:wa_raw;
 '''
 for label in ('gold','gate'):
  s+='wire[309:0] '+label+'_out;\n'+label+'_bus b_'+label+'(.clk(clk),.rst_n(rst_n),.iv(iv),.ir('+label+'_out[0]),.ia(ia),.iov('+label+'_out[1]),.ior(ior),.idata('+label+'_out[65:2]),.ierr('+label+'_out[66]),.dv(dv),.dr('+label+'_out[67]),.da(da),.dw(dw),.wa(wa),.dm(dm),.dwrite(dwrite),.dov('+label+'_out[68]),.dor(dor),.ddata('+label+'_out[100:69]),.derr('+label+'_out[101]),.uart_tx('+label+'_out[102]),.timer_irq('+label+'_out[103]),.gpio_out(),.tohost(),.formal_state('+label+'_out[309:104]),.formal_uart_ready(formal_uart_ready),.formal_uart_tx(formal_uart_tx),.formal_iq0(formal_iq0),.formal_iq1(formal_iq1),.formal_dq0(formal_dq0),.formal_dq1(formal_dq1));\n'
 s+='assign equal=gold_out==gate_out;endmodule\n';p.write_text(s);inputs.append(p);generated.append(p)
 def linux(p):return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
 script='read_verilog -sv '+' '.join(linux(p) for p in generated)+'; prep -top miter -flatten; async2sync; opt; sat -verify -seq 2 -tempinduct -set-init-zero -prove equal 1';x=subprocess.run(['wsl.exe','-d','Ubuntu','--','yosys','-p',script],cwd=ROOT,capture_output=True,timeout=180);(out/'sat.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0 and b'SUCCESS!' in x.stdout
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=['PASS temporal induction of actual bus full state/output, four RAM enables and UART send under SAT-proven write publication contract; shared arbitrary RAM read values/UART ready/UART tx, no assumption of ready=1 or zero read data'],input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print(a.variant,'full bus induction PASS')
if __name__=='__main__':main()
