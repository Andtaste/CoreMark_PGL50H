"""Prove the paired-primary shortcut against the complete EX prediction logic."""
from pathlib import Path
import hashlib,json,subprocess,argparse
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',default='dual_boundary_pair');a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);out=src/'annul_proof';out.mkdir(exist_ok=True)
 fetch=src/'nc_fetch.v';decoder=ROOT/'hardware/pds/source/core/nc_decode.v';execute=src/'nc_execute.v';fun=fetch.read_text().split(' function[8:0] classify_parts;',1)[1].split(' endfunction',1)[0]
 proof=out/'annul_proof.v';proof.write_text('module annul_proof(input[31:0] insn,pc,a,b,pred_target,output equal);\n function[8:0] classify_parts;'+fun+' endfunction\n'+'''
 wire[8:0] parts=classify_parts(insn);wire allowed=|parts[8:3];
 wire[3:0] kind;wire[31:0] imm;wire wr,illegal;wire[4:0] rd;wire[18:0] control;
 nc_decode d(.insn(insn),.kind(kind),.imm(imm),.use1(),.use2(),.write_rd(wr),.serial(),.illegal(illegal),.control(control),.rs1(),.rs2(),.rd(rd),.csr_exists(1'b0),.csr_writable(1'b0));
 wire wrong,taken;wire[276:0] result;
 nc_execute #(.ENABLE_DIV(0)) e(.clk(1'b0),.rst_n(1'b1),.clear(1'b0),.valid(1'b1),.ready(),
 .packet({kind,pc,insn,a,b,imm,32'b0,rd,wr,illegal,1'b0}),.control(control),.out_valid(),.out_ready(1'b1),
 .redirect_needed(),.redirect_target(),.prediction({pred_target[31],1'b0,pred_target[29:0]}),.prediction_wrong(wrong),.branch_taken(taken),.out_packet(result),.memory_aux());
 wire shortcut=control[16] && taken && imm!=32'd4;
 assign equal=!allowed || result[2] || wrong==shortcut;
 endmodule
''')
 def linux(p):return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
 divide=ROOT/'hardware/pds/source/core/nc_divide.v'
 cmd=['wsl.exe','-d','Ubuntu','--','yosys','-p',f'read_verilog -sv {linux(decoder)} {linux(divide)} {linux(execute)} {linux(proof)}; prep -top annul_proof -flatten; sat -verify -prove equal 1']
 x=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=180);(out/'sat.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0 and b'SUCCESS!' in x.stdout,(x.stdout+x.stderr)[-2500:]
 inputs=[Path(__file__).resolve(),fetch,decoder,divide,execute,src/'nc_core.v',proof]
 (out/'result.json').write_text(json.dumps(dict(status='PASS',variant=a.variant,tests=['PASS SAT: under actual paired-primary instruction admission and not-taken prediction, shortcut equals complete EX prediction_wrong whenever primary has no fault; all operands/PC/target bits unconstrained'],input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print('paired annul SAT PASS')
if __name__=='__main__':main()
