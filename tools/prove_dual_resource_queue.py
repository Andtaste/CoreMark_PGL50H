"""SAT-check the actual generated queue encoder/decoder against its parent."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def linux(p):return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args()
 src=ROOT/('simulation/results/load_bp_'+a.variant);out=src/'resource_proof';out.mkdir(exist_ok=True)
 c=(src/'nc_core.v').read_text();old=(ROOT/'simulation/results/load_bp_dual_boundary_next_pairbranch/nc_core.v').read_text()
 # The checked expressions are extracted from the actual generated RTL.
 enc=c[c.index(' wire queue_store='):c.index(' // Input credit is still')]
 dec=c[c.index(' wire[31:0] compact_value='):c.index(' nc_memory #')]
 ref=old[old.index(' wire queue_store='):old.index(' // Input credit is still')]
 ref+=' assign {compact_side,compact_packet}=incoming_packet;\n'
 ref+=old[old.index(' wire[31:0] compact_value='):old.index(' nc_memory #')]
 def module(name,body):
  return 'module '+name+'(input[203:0] ex_packet,input[276:0] execute_packet,input[31:0] execute_aux,input[2:0] ex_tag,input[64:0] side_result,output[279:0] mem_packet);\n'+body+'\nendmodule\n'
 gate=out/'gate.v';gate.write_text(module('gate',enc+'assign queued_storage={incoming_packet[248:117],incoming_packet[84:0]};\nassign {compact_side,compact_packet}=queued_packet;\n'+dec))
 gold=out/'gold.v';gold.write_text(module('gold',ref))
 wrapper=out/'miter.v';wrapper.write_text('''module miter(input[203:0] packet,input[18:0] control,input[31:0] prediction,input[2:0] tag,input[64:0] side,output equal);
 wire[276:0] result;wire[31:0] aux;wire[279:0] a,b;
 nc_execute #(.ENABLE_DIV(0)) ex(.clk(1'b0),.rst_n(1'b1),.clear(1'b0),.valid(1'b1),.ready(),.packet(packet),.control(control),.out_valid(),.out_ready(1'b1),.redirect_needed(),.redirect_target(),.prediction(prediction),.prediction_wrong(),.branch_taken(),.out_packet(result),.memory_aux(aux));
 gold g(.ex_packet(packet),.execute_packet(result),.execute_aux(aux),.ex_tag(tag),.side_result(side),.mem_packet(a));
 gate h(.ex_packet(packet),.execute_packet(result),.execute_aux(aux),.ex_tag(tag),.side_result(side),.mem_packet(b));
 assign equal=a==b;
 endmodule
 ''')
 inputs=[src/'nc_core.v',src/'nc_execute.v',ROOT/'simulation/results/load_bp_dual_boundary_next_pairbranch/nc_core.v',gate,gold,wrapper,Path(__file__).resolve()]
 divider=ROOT/'hardware/pds/source/core/nc_divide.v';inputs.append(divider)
 script='read_verilog -sv '+' '.join(linux(p) for p in [src/'nc_execute.v',divider,gate,gold,wrapper])+'; hierarchy -top miter; prep -top miter -flatten; opt; sat -verify -prove equal 1 -show-inputs'
 x=subprocess.run(['wsl.exe','-d','Ubuntu','--','yosys','-p',script],capture_output=True,timeout=300);(out/'proof.log').write_bytes(x.stdout+x.stderr)
 assert x.returncode==0,(x.stdout+x.stderr)[-4000:]
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=['SAT exact 280-bit MEM packet equivalence for all main input bits, controls, predictions, tags and side bits; arbitrary illegal/fetch faults and address wrap included. Divider result stubbed because queue next-PC invariant is independent of DIV value. FIFO storage order uses unchanged nc_fifo.'],input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n')
 print('PASS actual queue encoder/decoder SAT',a.variant)
if __name__=='__main__':main()
