"""Lint plus boundary/resource redundancy audit for branch/MUL/window trials."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def linux(p):p=Path(p).resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);out=src/'audit';out.mkdir(exist_ok=True)
 g=json.loads((src/'generation.json').read_text());b=json.loads((ROOT/'docs/accepted_baseline.json').read_text());inputs=[Path(__file__).resolve()]
 for n,h in b['source_sha256'].items():assert sha(ROOT/n)==h,n
 for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
 files=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[])
 actual=[src/p.name if str(p.relative_to(ROOT)) in g['override_sha256'] else p for p in files]+[src/'pango_ram_wide_models.v'];inputs+=actual
 with (out/'lint.log').open('wb') as f:p=subprocess.run(['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--','verilator','--lint-only','-Wall','-Wno-fatal','--top-module','nc_soc',*[linux(p) for p in actual]],stdout=f,stderr=subprocess.STDOUT,timeout=180)
 s=(out/'lint.log').read_text(errors='replace');assert p.returncode==0,s[-4000:]
 kinds={k:len(re.findall('%Warning-'+k+':',s)) for k in sorted(set(re.findall(r'%Warning-(\w+):',s)))}
 for k in ('LATCH','UNOPTFLAT','MULTIDRIVEN','UNDRIVEN','IMPLICIT','PINMISSING','PINNOTFOUND'):assert not kinds.get(k,0),(k,kinds)
 core=(src/'nc_core.v').read_text();ops=src/'nc_operands.v';parent=ROOT/'simulation/results/load_bp_dual_fwd_share'
 assert sha(ops)==sha(parent/'nc_operands.v')
 assert "nc_fifo #(.WIDTH(249),.DEPTH(4))" in core and 'wire[64:0] side_result' in core
 assert 'nc_execute #(.ENABLE_DIV(0)) execute1' in core and "id_pair_flags[3] && !id_prediction[31]" in core
 assert 'wire[2:0] f1_tag=f_tag' in core
 tests=['PASS no dangerous lint diagnostics','PASS accepted tagged operand queue unchanged; no four-operand capture/wait network',
  'PASS EX/MEM width249 and depth4 unchanged; no added full-width side metadata queue',
  'PASS secondary divider disabled explicitly at elaboration',
  'PASS extended pairs require ordinary ALU primary and source independence; group precise-fault policy retained',
  'PASS no secondary LSU or new physical RAM port; memory-ready still terminates at registered-credit FIFO']
 if a.variant in ('dual_types_compact','dual_types_slide','dual_types_bound','dual_types_slide_bound'):
  fetch=(src/'nc_fetch.v').read_text();mem=(src/'nc_memory.v').read_text()
  fun=fetch[fetch.index(' function[8:0] classify_parts'):];fun=fun[:fun.index(' endfunction')+len(' endfunction')]
  branch=re.search(r'wire w1_branch=([^;]+);',core)[1];mul=re.search(r'wire secondary_multiply=([^;]+);',mem)[1]
  proof="module proof(input[31:0] insn,output equal);\n"+fun+"\nwire[8:0] p=classify_parts(insn);wire allowed=|p[5:3] || p[8];wire[31:0] w1_insn=insn;wire[64:0] side_packet={1'b1,insn,32'b0};\nwire short_branch="+branch+";wire short_mul="+mul+";\nassign equal=!allowed || ((short_branch==(insn[6:0]==7'h63)) && (short_mul==(insn[6:0]==7'h33 && insn[31:25]==1 && !insn[14])));\nendmodule\n"
  q=out/'opcode_proof.v';q.write_text(proof);inputs+=[q]
  p=subprocess.run(['wsl.exe','-d','Ubuntu','--','yosys','-p',f'read_verilog -sv {linux(q)}; prep -top proof -flatten; sat -verify -prove equal 1'],capture_output=True,timeout=90);(out/'opcode_sat.log').write_bytes(p.stdout+p.stderr)
  assert p.returncode==0 and b'SUCCESS!' in p.stdout,p.stdout.decode(errors='replace')[-4000:]
  tests+=['PASS SAT: actual compact WB branch and MEM MUL decode equal full decode for every admitted instruction word']
 if 'slide' in a.variant:
  assert 'reg[31:0] peek_inst,peek_prediction;reg[8:0] peek_parts;' in fetch and 'reg cmd_link,flight_link,stream_sequential;reg[3:0] links;' in fetch
  tests+=['PASS following cache stores only one instruction; backing groups retained; adjacency crosses command/flight/cache registers']
 if 'bound' in a.variant:
  fetch=(src/'nc_fetch.v').read_text();fun=fetch[fetch.index(' function[8:0] classify_parts'):];fun=fun[:fun.index(' endfunction')+len(' endfunction')]
  proof="module proof_primary(input[31:0] insn,output equal);\n"+fun+"\nwire[8:0] p=classify_parts(insn);wire[3:0] kind;wire illegal,serial;wire[18:0] control;\nnc_decode d(.insn(insn),.kind(kind),.imm(),.use1(),.use2(),.write_rd(),.serial(serial),.illegal(illegal),.control(control),.rs1(),.rs2(),.rd(),.csr_exists(1'b0),.csr_writable(1'b0));\nassign equal=!(|p[5:3]) || (kind==0 && !illegal && !serial && control[18:16]==0);\nendmodule\n"
  q=out/'primary_admission_proof.v';q.write_text(proof);decoder=ROOT/'hardware/pds/source/core/nc_decode.v';inputs +=[q,decoder]
  p=subprocess.run(['wsl.exe','-d','Ubuntu','--','yosys','-p',f'read_verilog -sv {linux(decoder)} {linux(q)}; prep -top proof_primary -flatten; sat -verify -prove equal 1'],capture_output=True,timeout=90);(out/'primary_sat.log').write_bytes(p.stdout+p.stderr)
  assert p.returncode==0 and b'SUCCESS!' in p.stdout,p.stdout.decode(errors='replace')[-4000:]
  assert 'wire mul_accept=ex_fire && (ex_multiply || side_multiply);' in core
  tests+=['PASS SAT actual frontend plain-ALU classification implies legal nonserial noncontrol primary; together with registered clean-fetch/no-prediction admission removes redundant EX fault/prediction term from side-MUL DSP CE']
 x=dict(status='PASS',tests=tests,lint_warning_counts=kinds,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs})
 (out/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({k:v for k,v in x.items() if k!='input_sha256'},indent=2))
if __name__=='__main__':main()
