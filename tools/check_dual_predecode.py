"""Check predecode truth table and flags/instruction alignment independently."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parent=ROOT/'simulation/results/load_bp_dual_issue_predecode';out=parent/'predecode_check';out.mkdir(exist_ok=True)
 fetch=parent/'nc_fetch.v';s=fetch.read_text();f=s[s.index(' function[4:0] classify;'):s.index(' endfunction')+len(' endfunction')]
 tb=out/'predecode_tb.v';tb.write_text('''`timescale 1ns/1ps
module predecode_tb;
 reg[31:0] id_insn=0;wire[4:0] flags=classify(id_insn);
 wire[3:0] kind;wire[31:0] imm;wire use1,use2,wr,serial,illegal;wire[4:0] a,b,d;wire[18:0] control;
 nc_decode decoder(.insn(id_insn),.kind(kind),.imm(imm),.use1(use1),.use2(use2),.write_rd(wr),.serial(serial),.illegal(illegal),
 .control(control),.rs1(a),.rs2(b),.rd(d),.csr_exists(1'b1),.csr_writable(1'b1));
'''+f+'''
 wire expected=!illegal && !serial && (kind==0 || kind==4 || kind==5 || (kind==6 && !id_insn[14]));
 wire expected_alu=!illegal && !serial && kind==0;
 integer op,f3,f7,n=0;
 initial begin
  for(op=0;op<128;op=op+1) for(f3=0;f3<8;f3=f3+1) for(f7=0;f7<128;f7=f7+1) begin
   id_insn=(f7<<25)|(17<<20)|(5<<15)|(f3<<12)|(3<<7)|op;#1;
   if(flags[4]!==expected || flags[3]!==expected_alu || (expected && flags[2]!==wr) ||
      (expected_alu && (flags[0]!==use1 || flags[1]!==use2))) $fatal(1,"Predecode mismatch insn=%h flags=%b",id_insn,flags);
   n=n+1;
  end
  $display("PASS registered predecode combinations=%0d",n);$finish;
 end
endmodule
''')
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe');decoder=ROOT/'hardware/pds/source/core/nc_decode.v';logs=[]
 def run(cmd,name):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(out/name).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(name,p.stdout+p.stderr);return p.stdout.decode(errors='replace')
 run([iv,'-g2012','-s','predecode_tb','-o',out/'decode.vvp',decoder,tb],'decode_compile.log')
 t=run([vvp,out/'decode.vvp'],'decode.log');assert 'PASS registered predecode combinations=131072' in t;logs.append(t.strip())
 source=ROOT/'simulation/research/dual_issue/dual_units_tb.v';alignment=out/'dual_units_tb.v';s=source.read_text()
 s=s.replace('nc_fetch f(', 'wire[9:0] observed_flags;\n nc_fetch f(.pair_flags(observed_flags),')
 s=s.replace('if(!fault && inst!==word(pc))', 'if(!fault && observed_flags[4:0]!==f.classify(inst)) $fatal(1,"Primary flag ownership mismatch");\n    if(second && !fault && observed_flags[9:5]!==f.classify(inst1)) $fatal(1,"Secondary flag ownership mismatch");\n    if(!fault && inst!==word(pc))')
 alignment.write_text(s)
 rtl=[fetch,parent/'nc_regfile.v',ROOT/'hardware/pds/source/core/nc_btb.v']
 run([iv,'-g2012','-s','dual_units_tb','-o',out/'alignment.vvp',*rtl,alignment],'alignment_compile.log')
 t=run([vvp,out/'alignment.vvp'],'alignment.log');assert 'PASS dual units cycles=30000' in t;logs.append(t.strip())
 inputs=[Path(__file__).resolve(),fetch,decoder,tb,source,alignment,*rtl]
 x=dict(status='PASS',tests=logs,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs});(out/'result.json').write_text(json.dumps(x,indent=2)+'\n');print('\n'.join(logs))
if __name__=='__main__':main()
