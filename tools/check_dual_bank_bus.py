"""Prove actual bus full state/output and actual RAM CE expressions."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);ref=ROOT/'simulation/results/load_bp_dual_boundary_storewrite';out=src/'bank_bus_proof';out.mkdir(exist_ok=True);inputs=[Path(__file__).resolve()];generated=[];ramblocks=[];tests=[]
 for folder,label in ((ref,'gold'),(src,'gate')):
  p=folder/'nc_local_bus.v';s=p.read_text();ramblocks.append(s[s.index(' ram1_tdp ram_code('):].replace('.b_clk_en(ram0_ce)','.b_clk_en(da_fire && db0)').replace('.b_clk_en(ram1_ce)','.b_clk_en(da_fire && db1)'))
  ces=re.findall(r'\.b_clk_en\(([^)]*)\)',s);assert len(ces)==2;s=s.replace('module nc_local_bus #','module '+label+'_bus #').replace('output reg[31:0] tohost);','output reg[31:0] tohost,input formal_uart_ready,formal_uart_tx,input[63:0] formal_iq0,formal_iq1,input[31:0] formal_dq0,formal_dq1,output[205:0] formal_state);')
  begin=s.index(' nc_uart #(');end=s.index(' assign dr=',begin);s=s[:begin]+' assign uart_ready=formal_uart_ready;assign uart_tx=formal_uart_tx;\n'+s[end:];begin=s.index(' ram1_tdp ram_code(');s=s[:begin]+''' assign iq0=formal_iq0;assign iq1=formal_iq1;assign dq0=formal_dq0;assign dq1=formal_dq1;
 assign formal_state={uart_send,(ia_fire && ib0 && !ia[1] && !ia[0]),(ia_fire && ib1 && !ia[1] && !ia[0]),(@CE0@),(@CE1@),ipending,ibank,ierror,dpending,dbank,dis_ram,derror,mmio_data,mtime,mtimecmp,gpio,tohost};
 endmodule
 '''.replace('@CE0@',ces[0]).replace('@CE1@',ces[1]);f=out/(label+'.v');f.write_text(s);generated.append(f);inputs +=[p,f]
 assert ramblocks[0]==ramblocks[1],'RAM address/data/mask/write interface changed'
 def linux(p):return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
 for mode in (0,1):
  p=out/f'miter{mode}.v';s='''module miter(input clk,rst_n,iv,ior,dv,dor,dwrite,input[31:0] ia,da,dw,wa,input[3:0] dm,input[1:0] raw_banks,input formal_uart_ready,formal_uart_tx,input[63:0] formal_iq0,formal_iq1,input[31:0] formal_dq0,formal_dq1,output equal);
 wire[1:0] banks={2{dv}} & {(da>=32'h10000000 && da<32'h10008000),da<32'h00010000};
 '''
  for label in ('gold','gate'):
   param=f' #(.USE_RAM_REQUESTS({mode}))' if label=='gate' else '';extra=('.ram_requests('+('banks' if mode else 'raw_banks')+'),') if label=='gate' else ''
   s+='wire[309:0] '+label+'_out;\n'+label+'_bus'+param+' b_'+label+'('+extra+'.clk(clk),.rst_n(rst_n),.iv(iv),.ir('+label+'_out[0]),.ia(ia),.iov('+label+'_out[1]),.ior(ior),.idata('+label+'_out[65:2]),.ierr('+label+'_out[66]),.dv(dv),.dr('+label+'_out[67]),.da(da),.dw(dw),.wa(wa),.dm(dm),.dwrite(dwrite),.dov('+label+'_out[68]),.dor(dor),.ddata('+label+'_out[100:69]),.derr('+label+'_out[101]),.uart_tx('+label+'_out[102]),.timer_irq('+label+'_out[103]),.gpio_out(),.tohost(),.formal_state('+label+'_out[309:104]),.formal_uart_ready(formal_uart_ready),.formal_uart_tx(formal_uart_tx),.formal_iq0(formal_iq0),.formal_iq1(formal_iq1),.formal_dq0(formal_dq0),.formal_dq1(formal_dq1));\n'
  s+='assign equal=gold_out==gate_out;endmodule\n';p.write_text(s);inputs.append(p);script='read_verilog -sv '+' '.join(linux(p) for p in [*generated,p])+'; prep -top miter -flatten; async2sync; opt; sat -verify -seq 2 -tempinduct -set-init-zero -prove equal 1';x=subprocess.run(['wsl.exe','-d','Ubuntu','--','yosys','-p',script],cwd=ROOT,capture_output=True,timeout=180);(out/f'mode{mode}.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0 and b'SUCCESS!' in x.stdout,(x.stdout+x.stderr)[-2000:];tests.append(f'PASS actual bus full state, response, four RAM enables and UART send, mode={mode}; arbitrary UART ready/tx/RAM read values, raw qualifiers arbitrary in default mode and MEM-proved qualifier contract in enabled mode')
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print(a.variant,'bus induction PASS 2')
if __name__=='__main__':main()
