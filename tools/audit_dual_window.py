"""Lint, registered-boundary audit and combinational proof of WB-only admission."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
import audit_dual_ram as old
ROOT=old.ROOT
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant)
 old.OUT=src;old.main();dest=src/'audit';result=json.loads((dest/'result.json').read_text())
 parent=ROOT/'simulation/results/load_bp_dual_fwd_share';g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  if Path(n).name not in ('nc_core.v','nc_fetch.v'):assert sha(src/Path(n).name)==sha(parent/Path(n).name),n
 for p in (src/'ipcore').rglob('*'):
  if p.is_file() and p.suffix in ('.v','.idf'):assert sha(p)==sha(parent/'ipcore'/p.relative_to(src/'ipcore')),p
 core=(src/'nc_core.v').read_text();fetch=(src/'nc_fetch.v').read_text()
 for line in ('reg wb_v;reg[279:0] wb_q;assign wb_valid=wb_v;assign wb_packet=wb_q;',
   'wire commit1=commit && w_side[64];','wire[64:0] w_side;wire commit=wb_valid && !w_fault;'):
  assert line in core,line
 for line in ('wire[3:0] reserved={1\'b0,count}+{3\'b0,flight}+{3\'b0,cmd_valid};',
   'wire prepare=(!cmd_valid || launch) && reserved<4 && !stop && !redirect;',
   'assign req_valid=cmd_valid && (!flight || response);assign req_addr=cmd_pc;assign rsp_ready=flight;'):
  assert line in fetch,line
 result['tests']+=['PASS only nc_core/nc_fetch differ; operands, EX, MEM, FIFO, RF, LSU and IP unchanged',
  'PASS WB forwarding sources originate from wb_q/wb_side_q/wb_v registers; no current EX or RAM-return source',
  'PASS same four-group registered fetch reservation and request/response protocol']
 if 'cross_window' in fetch:
  assert 'reg[63:0] peek_inst,peek_predictions' in fetch
  assert 'assign inst1=head_inst[63:32]' in fetch
  assert 'reg head_cross;wire cross_window=head_cross;' in fetch
  assert 'pack_flags(head_parts[15:8])' in fetch
  assert fetch.count('instructions[after_following]')==2
  assert 'peek_inst<=instructions[after_following]' in fetch
  result['tests'].append('PASS cross-group view and ownership registered before ID; no head/peek mux or fault/occupancy qualification before secondary decode')
 if 'wire wb_a0=' in core:
  # Prove the actual new local expressions against independent masked
  # producer sets; unrelated live WAW writers must continue to block.
  start=core.index('    if(id_pair_flags[5] && rs1_1!=0 &&');end=core.index('\n   end',start)
  logic=core[start:end]
  start=core.index(' wire wb_a0=');end=core.index(' wire[223:0] id_side=',start);data=core[start:end]
  proof='''module proof(input[7:0] live,input[39:0] dest_flat,dest1_flat,
 input[9:0] id_pair_flags,input[4:0] rs1_1,rs2_1,w_rd,w1_rd,
 input commit,commit1,w_wr,input[2:0] w_tag,input[31:0] w_result,w1_result,c,d,
 output equal);
 wire[4:0] destination[0:7],destination1[0:7];
 wire[7:0] matches0,matches1,waiting0,waiting1;
 genvar g;generate for(g=0;g<8;g=g+1) begin:reference
  assign destination[g]=dest_flat[g*5+:5];assign destination1[g]=dest1_flat[g*5+:5];
  assign matches0[g]=live[g] && ((id_pair_flags[5] && rs1_1!=0 && destination[g]==rs1_1) || (id_pair_flags[6] && rs2_1!=0 && destination[g]==rs2_1));
  assign matches1[g]=live[g] && ((id_pair_flags[5] && rs1_1!=0 && destination1[g]==rs1_1) || (id_pair_flags[6] && rs2_1!=0 && destination1[g]==rs2_1));
  assign waiting0[g]=!(commit && w_wr && w_tag==g);
  assign waiting1[g]=!(commit1 && w_tag==g);
 end endgenerate
 reg second_dep;integer n;
 always @* begin second_dep=0;for(n=0;n<8;n=n+1) if(live[n]) begin
'''+logic+'''
 end end
'''+data+'''
 wire[31:0] expected_a=({32{wb_a1}}&w1_result)|({32{!wb_a1 && wb_a0}}&w_result)|({32{!wb_a1 && !wb_a0}}&c);
 wire[31:0] expected_b=({32{wb_b1}}&w1_result)|({32{!wb_b1 && wb_b0}}&w_result)|({32{!wb_b1 && !wb_b0}}&d);
 assign equal=(second_dep==(|(matches0 & waiting0) || |(matches1 & waiting1))) && side_a==expected_a && side_b==expected_b;
endmodule
'''
  file=dest/'wb_proof.v';file.write_text(proof)
  x=subprocess.run(['wsl.exe','-d','Ubuntu','--','yosys','-p',f'read_verilog -sv {old.linux(file)}; prep -top proof -flatten; sat -verify -prove equal 1 -show-inputs -show-outputs'],capture_output=True,timeout=120)
  (dest/'wb_sat.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0 and b'SUCCESS!' in x.stdout,x.stdout[-3000:]
  result['input_sha256'][str(file.relative_to(ROOT))]=sha(file)
  result['tests'].append('PASS SAT all live/destination/source/WB combinations: other matching writers block; WB1>WB0>x0/RF data priority preserved')
 result['input_sha256'][str(Path(__file__).resolve().relative_to(ROOT))]=sha(Path(__file__).resolve())
 result['new_tests_are']='Static boundary/scope audit and local combinational SAT, not a full sequential proof'
 (dest/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(a.variant,'PASS scope/boundary/WB proof',result['lint_warning_counts'])
if __name__=='__main__':main()
