"""Prove full classifier truth table and compare qualified decode outputs."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def linux(p):p=p.resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def functions(p):
 s=p.read_text();start=s.index(' function[');end=s.index('\n reg[',start);return s[start:end]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_if_class','dual_if_parts'),required=True);a=ap.parse_args()
 out=ROOT/('simulation/results/load_bp_'+a.variant);dest=out/'classification';dest.mkdir(exist_ok=True)
 ref=ROOT/'simulation/results/load_bp_dual_ram_logic/nc_fetch.v';fetch=out/'nc_fetch.v'
 old=functions(ref);new=functions(fetch)
 proof=dest/'proof.v';proof.write_text('module reference(input[31:0] insn,output[4:0] flags);\n'+old+'\nassign flags=classify(insn);endmodule\n'
  +'module candidate(input[31:0] insn,output[4:0] flags);\n'+new+'\nassign flags=classify(insn);endmodule\n'
  +'module proof(input[31:0] insn,output equal);wire[4:0] a,b;reference r(insn,a);candidate c(insn,b);assign equal=a==b;endmodule\n')
 def run(cmd,name,timeout=180):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=timeout);(dest/name).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(name,(p.stdout+p.stderr)[-4000:]);return p.stdout.decode(errors='replace')
 script='read_verilog -sv '+linux(proof)+'; prep -top proof -flatten; sat -verify -prove equal 1 -show-inputs -show-outputs'
 t=run(['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--','yosys','-Q','-T','-p',script],'proof.log');assert 'SUCCESS' in t
 tb=dest/'decode_tb.v';tb.write_text('''`timescale 1ns/1ps
module decode_tb;
 reg[31:0] insn=0;wire[4:0] flags=classify(insn);
 wire[3:0] kind;wire[31:0] imm;wire u1,u2,wr,serial,illegal;wire[4:0] a,b,d;wire[18:0] control;
 nc_decode dec(.insn(insn),.kind(kind),.imm(imm),.use1(u1),.use2(u2),.write_rd(wr),.serial(serial),.illegal(illegal),
 .control(control),.rs1(a),.rs2(b),.rd(d),.csr_exists(1'b1),.csr_writable(1'b1));
'''+new+'''
 wire expected=!illegal && !serial && (kind==0 || kind==4 || kind==5 || (kind==6 && !insn[14]));
 wire alu=!illegal && !serial && kind==0;
 integer op,f3,f7,n=0;
 initial begin
  for(op=0;op<128;op=op+1) for(f3=0;f3<8;f3=f3+1) for(f7=0;f7<128;f7=f7+1) begin
   insn=(f7<<25)|(17<<20)|(5<<15)|(f3<<12)|(3<<7)|op;#1;
   if(flags[4]!==expected || flags[3]!==alu || (expected && flags[2]!==wr) ||
      (alu && (flags[0]!==u1 || flags[1]!==u2))) $fatal(1,"Classification mismatch insn=%h flags=%b",insn,flags);
   n=n+1;
  end
  $display("PASS IF classification decoder combinations=%0d",n);$finish;
 end
endmodule
''')
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';decoder=ROOT/'hardware/pds/source/core/nc_decode.v'
 run([iv,'-g2012','-s','decode_tb','-o',dest/'decode.vvp',decoder,tb],'compile.log')
 t=run([iv.with_name('vvp.exe'),dest/'decode.vvp'],'simulation.log');assert 'PASS IF classification decoder combinations=131072' in t,t
 inputs=[ref,fetch,proof,tb,decoder,Path(__file__).resolve()]
 x=dict(status='PASS',variant=a.variant,tests=['PASS SAT: all five classification bits equal for every binary 32-bit instruction',t.strip()],
  scope='Combinational classifier proof; registered ownership separately exercised by dual units and whole-core tests',input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs})
 (dest/'result.json').write_text(json.dumps(x,indent=2)+'\n');print('\n'.join(x['tests']))
if __name__=='__main__':main()
