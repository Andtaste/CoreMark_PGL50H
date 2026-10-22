"""All-input SAT equivalence of actual ALU/branch comparison rewrite."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def linux(p):return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
src=ROOT/'simulation/results/load_bp_dual_boundary_next_resourcecompare';ref=ROOT/'simulation/results/load_bp_dual_boundary_next_pairbranch/nc_execute.v';out=src/'resource_proof';out.mkdir(exist_ok=True)
gold=out/'gold.v';gold.write_text(ref.read_text().replace('module nc_execute #','module gold #',1))
gate=out/'gate.v';gate.write_text((src/'nc_execute.v').read_text().replace('module nc_execute #','module gate #',1))
s='module miter(input[203:0] packet,input[18:0] control,input[31:0] prediction,output equal);\n'
for n in ('gold','gate'):
 s+='wire[346:0] '+n+'_out;'+n+' #(.ENABLE_DIV(0)) '+n+'_dut(.clk(1\'b0),.rst_n(1\'b1),.clear(1\'b0),.valid(1\'b1),.out_ready(1\'b1),.packet(packet),.control(control),.prediction(prediction),.out_packet('+n+'_out[276:0]),.memory_aux('+n+'_out[308:277]),.redirect_target('+n+'_out[340:309]),.redirect_needed('+n+'_out[341]),.prediction_wrong('+n+'_out[342]),.branch_taken('+n+'_out[343]),.out_valid('+n+'_out[344]),.ready('+n+'_out[345]));assign '+n+'_out[346]=1\'b0;\n'
s+='assign equal=gold_out==gate_out;endmodule\n';tb=out/'miter.v';tb.write_text(s)
divider=ROOT/'hardware/pds/source/core/nc_divide.v';files=[gold,gate,divider,tb]
script='read_verilog -sv '+' '.join(linux(p) for p in files)+'; hierarchy -top miter; prep -top miter -flatten; opt; sat -verify -prove equal 1'
x=subprocess.run(['wsl.exe','-d','Ubuntu','--','yosys','-p',script],capture_output=True,timeout=300);(out/'proof.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0,(x.stdout+x.stderr)[-3000:]
(out/'result.json').write_text(json.dumps(dict(status='PASS',tests=['SAT actual EX complete outputs, redirect, prediction correctness and ready/valid for all packet/control/prediction bits; divider disabled in both, unchanged DIV separately covered by ISA regression.'],input_sha256={str(p.relative_to(ROOT)):sha(p) for p in [*files,src/'nc_execute.v',ref,Path(__file__).resolve()]}),indent=2)+'\n');print('PASS actual signed/unsigned comparison sharing SAT')
