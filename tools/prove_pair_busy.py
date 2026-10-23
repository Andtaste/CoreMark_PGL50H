"""Prove redundant busy next-state against ordered ledger updates for all inputs."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
trial=ROOT/'simulation/results/autonomous_20261022/pair_busy'
parent=ROOT/json.loads((trial/'parent_baseline.json').read_text())['project_directory']/'source/core/nc_core.v'
candidate=trial/'source/core/nc_core.v'
gold=parent.read_text();actual=candidate.read_text()
# Bind the independent ledger reference to the exact production update rules.
for statement in ['if(wb_valid) begin live[w_tag]<=0;head<=w_tag+1\'b1;end',
 'if(issue) begin live[tail]<=1;destination[tail]<=id_wr ? rd : 0;destination1[tail]<=pair_candidate && id_pair_flags[7] ? rd1 : 0;tail<=tail+1\'b1;end',
 'destination1[redirect_tag]<=0;',
 'for(r=0;r<8;r=r+1) if(((r-head)&7)>((redirect_tag-head)&7)) live[r]<=0;',
 'if(do_trap || irq_take) begin']:
 assert statement in gold and statement in actual,statement
fragment=actual[actual.index(' reg[31:0] pair_busy_next;'):actual.index(' always @(posedge clk or negedge rst_n) begin',actual.index(' reg[31:0] pair_busy_next;'))]
text='''module miter(input wire[7:0] live,input wire[39:0] dest0,dest1,
 input wire[2:0] head,tail,w_tag,redirect_tag,
 input wire wb_valid,issue,id_wr,pair_candidate,side_wr,branch_redirect,do_trap,irq_take,
 input wire[4:0] rd,rd1,output wire equal);
 wire[4:0] destination[0:7],destination1[0:7];
 wire[9:0] id_pair_flags={2'b0,side_wr,7'b0};
 genvar g;generate for(g=0;g<8;g=g+1) begin
  assign destination[g]=dest0[5*g+:5];assign destination1[g]=dest1[5*g+:5];
 end endgenerate
'''+fragment+'''
 reg[7:0] ref_live;reg[4:0] ref_d0[0:7],ref_d1[0:7];
 reg[31:0] expected;integer i;
 always @* begin
  ref_live=live;
  for(i=0;i<8;i=i+1) begin ref_d0[i]=destination[i];ref_d1[i]=destination1[i];end
  if(wb_valid) ref_live[w_tag]=0;
  if(issue) begin
   ref_live[tail]=1;ref_d0[tail]=id_wr ? rd : 0;
   ref_d1[tail]=pair_candidate && side_wr ? rd1 : 0;
  end
  if(branch_redirect) begin
   ref_d1[redirect_tag]=0;
   for(i=0;i<8;i=i+1) if(((i-head)&7)>((redirect_tag-head)&7)) ref_live[i]=0;
  end
  if(do_trap || irq_take) ref_live=0;
  expected=0;
  for(i=0;i<8;i=i+1) if(ref_live[i]) begin
   expected=expected | (32'b1<<ref_d0[i]) | (32'b1<<ref_d1[i]);
  end
  expected[0]=0;
 end
 assign equal=expected==((do_trap || irq_take) ? 32'b0 : pair_busy_next);
endmodule
'''
out=trial/'busy_transition_proof';out.mkdir(exist_ok=True)
bench=out/'miter.v';bench.write_text(text)
linux='/mnt/'+bench.drive[0].lower()+bench.as_posix()[2:]
cmd=f'read_verilog {linux}; prep -top miter; flatten; memory_map; opt; sat -verify -prove equal 1 -show-inputs'
r=subprocess.run(['wsl.exe','-d','Ubuntu','--','yosys','-p',cmd],capture_output=True,timeout=180)
(out/'yosys.log').write_bytes(r.stdout+r.stderr)
assert r.returncode==0 and b'SUCCESS!' in r.stdout,r.stdout[-3000:]
(out/'result.json').write_text(json.dumps(dict(status='PASS',scope='Arbitrary two-state ledger and update inputs: redundant bitmap next-state equals ordered parent ledger update; simultaneous commit/issue/squash/trap included. Reset sets both to zero. Not a whole-core formal proof.',input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [parent,candidate,bench,Path(__file__)]}),indent=2)+'\n')
print('PASS arbitrary-input busy state-transition equivalence')
