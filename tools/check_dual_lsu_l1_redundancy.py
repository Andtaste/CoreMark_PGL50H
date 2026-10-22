"""Bounded check whether registered secondary returns add anything to existing W1."""
from pathlib import Path
import json,hashlib,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def linux(p):p=p.resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def main():
 variant=sys.argv[1];src=ROOT/('simulation/results/load_bp_'+variant);out=src/'redundancy_checks';out.mkdir(exist_ok=True)
 q=out/'l1_proof.v';q.write_text('''module l1_proof(input clk,rst_n,kill,valid,req_ready,req1_ready,req_nofault,rsp_valid,rsp1_valid,rsp_error,mul_ready,
 input[279:0] packet,input[96:0] side_packet,input[31:0] rsp_data,rsp1_data,mul_data,output ok);
 wire done,l1;wire[279:0] wp;wire[64:0] ws;wire[2:0] lt;wire[31:0] ld;
 nc_memory m(.clk(clk),.rst_n(rst_n),.kill(kill),.valid(valid),.ready(),.packet(packet),.side_packet(side_packet),.wb_valid(done),.wb_packet(wp),.wb_side(ws),
 .mul_ready(mul_ready),.mul_data(mul_data),.mul_tag(),.mul_consume(),.req_valid(),.req_ready(req_ready),GRANT.req_addr(),.req_data(),.req_mask(),.req_write(),
 .rsp_valid(rsp_valid),.rsp_ready(),.rsp_data(rsp_data),.rsp_error(rsp_error),.req1_valid(),.req1_ready(req1_ready),.req1_addr(),.req1_data(),.req1_mask(),.req1_write(),
 .rsp1_valid(rsp1_valid),.rsp1_ready(),.rsp1_data(rsp1_data),.load0_valid(),.load1_valid(l1),.load_tag(lt),.load0_data(),.load1_data(ld));
 reg wv;reg[279:0] wq;reg[64:0] sq;
 always @(posedge clk) if(done) begin wq<=wp;sq<=ws;end
 always @(posedge clk or negedge rst_n) if(!rst_n) wv<=0;else wv<=done;
 assign ok=!l1 || (wv && !wq[2] && sq[64] && sq[38:32]==7'h03 && sq[43:39]!=0 && lt==wq[279:277] && ld==sq[31:0]);
 endmodule
'''.replace('GRANT','.req_nofault(req_nofault),' if variant=='dual_lsu_pair' else ''))
 cmd=f'read_verilog -sv {linux(src/"nc_memory.v")} {linux(q)}; prep -top l1_proof -flatten; async2sync; opt; sat -seq 8 -set-init-zero -set-at 1 rst_n 0 -set-at 2 rst_n 1 -prove ok 1 -verify'
 p=subprocess.run(['wsl.exe','-d','Ubuntu','--','yosys','-p',cmd],cwd=ROOT,capture_output=True,timeout=180);(out/'proof.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,(p.stdout+p.stderr)[-2500:];assert b'SUCCESS!' in p.stdout
 x=dict(status='PASS',tests=['PASS bounded 8-cycle arbitrary-input proof: L1 broadcast always duplicates clean same-tag/same-data W1 broadcast'],limit='Bounded proof plus RTL implication inspection; no separate performance-removal experiment or full-core unbounded proof.',input_sha256={str(n.relative_to(ROOT)):sha(n) for n in (q,src/'nc_memory.v',src/'nc_core.v',Path(__file__).resolve())})
 (out/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(variant,'L1 redundancy proof PASS')
if __name__=='__main__':main()
