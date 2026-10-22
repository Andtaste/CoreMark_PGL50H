"""Combinational noninterference: extra ALU values cannot change EX control/addresses."""
from pathlib import Path
import subprocess,json,hashlib
ROOT=Path(__file__).resolve().parents[1];src=ROOT/'simulation/results/load_bp_dual_boundary_next_aluwake';out=src/'alu_control_proof';out.mkdir(exist_ok=True)
ref=ROOT/'simulation/results/load_bp_dual_boundary_storewrite/nc_execute.v';old=out/'old_execute.v';old.write_text(ref.read_text().replace('module nc_execute #','module old_nc_execute #',1))
proof='''module proof(input[203:0] packet,input[18:0] control,input[31:0] prediction,x,y,input valid,out_ready,output equal);
'''
for n,mod,alu in [('a','nc_execute','.alu_a(x),.alu_b(y),'),('b','nc_execute','.alu_a(packet[135:104]),.alu_b(packet[103:72]),'),('c','old_nc_execute','')]:
 proof+=f'''wire[276:0] p_{n};wire[31:0] t_{n},aux_{n};wire r_{n},v_{n},d_{n},w_{n},k_{n};
 {mod} #(.ENABLE_DIV(0)) u_{n}(.clk(1'b0),.rst_n(1'b1),.clear(1'b0),.valid(valid),.ready(r_{n}),.packet(packet),{alu}.control(control),.out_valid(v_{n}),.out_ready(out_ready),.redirect_needed(d_{n}),.redirect_target(t_{n}),.prediction(prediction),.prediction_wrong(w_{n}),.branch_taken(k_{n}),.out_packet(p_{n}),.memory_aux(aux_{n}));
'''
proof+='''assign equal=({r_a,v_a,d_a,t_a,w_a,k_a,aux_a,p_a[276:181],p_a[148:0]}=={r_b,v_b,d_b,t_b,w_b,k_b,aux_b,p_b[276:181],p_b[148:0]}) &&
 ({r_b,v_b,d_b,t_b,w_b,k_b,aux_b,p_b}=={r_c,v_c,d_c,t_c,w_c,k_c,aux_c,p_c});endmodule
'''
p=out/'proof.v';p.write_text(proof)
def linux(p):p=p.resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
divider=ROOT/'hardware/pds/source/core/nc_divide.v'
cmd=['wsl.exe','-d','Ubuntu','--','yosys','-p',f'read_verilog -sv {linux(divider)} {linux(src/"nc_execute.v")} {linux(old)} {linux(p)}; prep -top proof -flatten; sat -verify -prove equal 1']
x=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=180);(out/'proof.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0 and b'SUCCESS!' in x.stdout,(x.stdout+x.stderr)[-2500:]
inputs=[Path(__file__).resolve(),ref,old,p,divider,src/'nc_execute.v'];(out/'result.json').write_text(json.dumps(dict(status='PASS',tests=['SAT arbitrary ALU data cannot alter EX readiness, redirect, branch decision, next-PC, addresses, exception, store data or auxiliary fields','SAT tying separate ALU inputs to original operands exactly reproduces accepted combinational EX (divider disabled)'],input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}),indent=2)+'\n');print('PASS ALU input control noninterference and baseline EX equivalence')
