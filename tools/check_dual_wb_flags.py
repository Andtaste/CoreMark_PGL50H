"""Induct the actual WB capture block and observe retimed flags in real SoC."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=('proof','soc'),required=True);a=ap.parse_args();src=ROOT/'simulation/results/load_bp_dual_boundary_wbflags'
 if a.mode=='soc':
  base=ROOT/'tools/check_dual_store_simple_soc.py';s=base.read_text();needle="s=s.replace(' reg was_local;'";assert s.count(needle)==1;mon='''  if(dut.cpu.wb_valid && (dut.cpu.wb_forward0!==(dut.cpu.w_wr && dut.cpu.w_rd!=0) || dut.cpu.wb_forward1!==(dut.cpu.w_side[64] && !dut.cpu.w1_branch && dut.cpu.w1_insn[11:7]!=0))) $fatal(1,"Retimed WB eligibility differs from original metadata");
  was_local=dut.bus.da_fire''';s=s.replace(needle,"s=s.replace('  was_local=dut.bus.da_fire', "+repr(mon)+")\n "+needle);ns={'__file__':str(base),'__name__':'wb_flag_soc'};exec(compile(s,str(base),'exec'),ns);sys.argv=[str(base),'--variant','dual_boundary_wbflags'];ns['main']();p=src/'posted_soc_final/result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__));x['scope']+='; every valid WB has identical predecoded forwarding eligibility to original metadata';p.write_text(json.dumps(x,indent=2)+'\n');return
 out=src/'wb_flag_proof';out.mkdir(exist_ok=True);actual=src/'nc_core.v';s=actual.read_text();start=s.index(' always @(posedge clk) if(memory_done) begin');end=s.index(' always @(posedge clk) if(ex_fire)',start);capture=s[start:end];assert 'wb_forward0<=' in capture and 'wb_forward1<=' in capture
 ref=ROOT/'simulation/results/load_bp_dual_boundary_storewrite/nc_core.v';r=ref.read_text();assert '.w_valid(commit && w_wr && w_rd!=0)' in r and '.w1_valid(commit1 && w1_rd!=0)' in r and 'wire w1_branch=w1_insn[6]' in r
 p=out/'miter.v';p.write_text('''module miter(input clk,rst_n,memory_done,input[279:0] memory_packet,input[64:0] memory_side,output equal);
 reg wb_v;reg[279:0] wb_q;reg[64:0] wb_side_q;reg wb_forward0,wb_forward1;
 '''+capture+'''
 wire commit=wb_v && !wb_q[2];
 wire original0=commit && wb_q[3] && wb_q[15:11]!=0;
 wire original1=commit && wb_side_q[64] && !wb_side_q[38] && wb_side_q[43:39]!=0;
 assign equal={original0,original1}=={(commit && wb_forward0),(commit && wb_forward1)};
 endmodule
 ''')
 def linux(p):return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
 script='read_verilog -sv '+linux(p)+'; prep -top miter -flatten; async2sync; opt; sat -verify -seq 2 -tempinduct -set-init-zero -prove equal 1';x=subprocess.run(['wsl.exe','-d','Ubuntu','--','yosys','-p',script],cwd=ROOT,capture_output=True,timeout=180);(out/'sat.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0 and b'SUCCESS!' in x.stdout,(x.stdout+x.stderr)[-1500:];inputs=[Path(__file__).resolve(),actual,ref,p];(out/'result.json').write_text(json.dumps(dict(status='PASS',tests=['PASS temporal induction: actual WB packet/flag/valid capture block, arbitrary metadata/done/reset; both forwarding enables equal original packed-metadata equations including fault suppression'],input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print('WB eligibility induction PASS')
if __name__=='__main__':main()
