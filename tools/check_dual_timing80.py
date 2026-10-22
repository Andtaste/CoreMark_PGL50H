"""Timing-round checks without rewriting any prior candidate's evidence."""
from pathlib import Path
import argparse,hashlib,json,sys,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);ap.add_argument('--mode',choices=('contracts','proof','equivalence'),required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant)
 if a.mode=='contracts':
  base=ROOT/'tools/check_dual_boundary_launch.py';s=base.read_text().replace("'simulation/results/load_bp_dual_boundary_launch'",repr('simulation/results/load_bp_'+a.variant)).replace("'--variant','dual_boundary_launch'",repr('--variant')+','+repr(a.variant))
  ns={'__file__':str(base),'__name__':'timing80_contracts'};exec(compile(s,str(base),'exec'),ns);ns['main']()
  for sub in ('memory_checks','address_contract'):
   p=src/sub/'result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__));save(p,x)
  return
 out=src/('timing_'+a.mode);out.mkdir(exist_ok=True);inputs=[Path(__file__).resolve()];tests=[]
 if a.mode=='proof':
  fetch=src/'nc_fetch.v';decoder=ROOT/'hardware/pds/source/core/nc_decode.v';inputs +=[fetch,decoder,src/'nc_core.v']
  fun=fetch.read_text().split(' function[8:0] classify_parts;',1)[1].split(' endfunction',1)[0]
  proof=out/'jump_controls.v';proof.write_text('module jump_controls(input[31:0] insn,output equal);\n function[8:0] classify_parts;'+fun+' endfunction\n'+'''wire[8:0] p=classify_parts(insn);wire side_allowed=|p[5:3] || p[8];
 wire primary_allowed=|p[8:3];wire[18:0] control;
 nc_decode d(.insn(insn),.kind(),.imm(),.use1(),.use2(),.write_rd(),.serial(),.illegal(),.control(control),.rs1(),.rs2(),.rd(),.csr_exists(1'b0),.csr_writable(1'b0));
 assign equal=!(side_allowed || primary_allowed) || control[18:17]==0;
 endmodule
''');inputs +=[proof]
  def linux(p):return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
  x=subprocess.run(['wsl.exe','-d','Ubuntu','--','yosys','-p',f'read_verilog -sv {linux(decoder)} {linux(proof)}; prep -top jump_controls -flatten; sat -verify -prove equal 1'],cwd=ROOT,capture_output=True,timeout=180);(out/'sat.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0 and b'SUCCESS!' in x.stdout
  tests +=['PASS SAT: actual primary and secondary admission excludes JAL/JALR control for every instruction']
 else:
  ref=ROOT/'simulation/results/load_bp_dual_boundary_launch'
  for sub in ('performance','validation'):
   old=json.loads((ref/sub/'result.json').read_text());new=json.loads((src/sub/'result.json').read_text());assert new['status']=='PASS'
   for key in ('metrics','predictor','multiply','dual','boundary'):assert old[key]==new[key],(sub,key)
   inputs +=[ref/sub/'result.json',src/sub/'result.json'];tests +=['PASS '+sub+' exact metrics and all independent profile counters match accepted source']
  for name,ev in (('nc_operands.v','operand_checks'),):
   origin=ROOT/'simulation/results/load_bp_dual_joint_reg';p=origin/ev/'result.json';x=json.loads(p.read_text());assert x['status']=='PASS' and len(x['tests'])==3 and sha(src/name)==sha(origin/name)
   inputs +=[src/name,origin/name,p];tests +=['PASS exact-hash prepared five-source operand network: reuse 3x100000-cycle independent equivalence']
 save(out/'result.json',dict(status='PASS',variant=a.variant,tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}));print(a.mode,'PASS',a.variant)
if __name__=='__main__':main()
