"""Exhaustively compare local primary-pair decode with the full decoder."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def main():
 out=ROOT/'simulation/results/load_bp_dual_issue_finish/decode_check';out.mkdir(exist_ok=True)
 core=out.parent/'nc_core.v';s=core.read_text();block=s[s.index(' wire[6:0] pair_op='):s.index(' wire pair_candidate=')]
 tb=out/'pair_decode_tb.v';tb.write_text('''`timescale 1ns/1ps
module pair_decode_tb;
 reg[31:0] id_insn=0;reg exists=0,writable=0;
 wire[3:0] kind;wire[31:0] imm;wire use1,use2,wr,serial,illegal;wire[4:0] a,b,d;wire[18:0] control;
 nc_decode decoder(.insn(id_insn),.kind(kind),.imm(imm),.use1(use1),.use2(use2),.write_rd(wr),.serial(serial),.illegal(illegal),
 .control(control),.rs1(a),.rs2(b),.rd(d),.csr_exists(exists),.csr_writable(writable));
'''+block+'''
 wire expected=!illegal && !serial && (kind==0 || kind==4 || kind==5 || (kind==6 && !id_insn[14]));
 integer op,f3,f7,n=0;
 initial begin
  for(op=0;op<128;op=op+1) for(f3=0;f3<8;f3=f3+1) for(f7=0;f7<128;f7=f7+1) begin
   id_insn=(f7<<25)|(17<<20)|(5<<15)|(f3<<12)|(3<<7)|op;exists=f7[0];writable=f7[1];#1;
   if(primary_pair_legal!==expected || (expected && primary_pair_write!==wr)) $fatal(1,"Pair decode mismatch insn=%h",id_insn);
   n=n+1;
  end
  $display("PASS pair decode combinations=%0d",n);$finish;
 end
endmodule
''')
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe');decoder=ROOT/'hardware/pds/source/core/nc_decode.v'
 for cmd,name in (([iv,'-g2012','-s','pair_decode_tb','-o',out/'unit.vvp',decoder,tb],'compile.log'),([vvp,out/'unit.vvp'],'unit.log')):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=120);(out/name).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(name,p.stdout+p.stderr)
 t=(out/'unit.log').read_text();assert 'PASS pair decode combinations=131072' in t
 inputs=[core,decoder,tb,Path(__file__).resolve()]
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=[t.strip()],input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}),indent=2)+'\n')
 print(t.strip())
if __name__=='__main__':main()
