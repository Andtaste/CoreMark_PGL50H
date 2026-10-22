"""Compare admitted lane1 decode outputs with the original full decoder."""
from pathlib import Path
import json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1]
def main():
 out=ROOT/'simulation/results/load_bp_dual_ram_alu/decode_check';out.mkdir(exist_ok=True);core=out.parent/'nc_core.v';s=core.read_text()
 block=s[s.index(' wire[31:0] c,d;reg[31:0] id1_imm;'):s.index(' nc_regfile rf(')]
 tb=out/'lane1_decode_tb.v';tb.write_text('''`timescale 1ns/1ps
module lane1_decode_tb;
 reg[31:0] id_insn1=0;
'''+block+'''
 wire[3:0] kind;wire[31:0] imm;wire use1,use2,wr,serial,illegal;wire[4:0] a,b,dummy;wire[18:0] control;
 nc_decode reference(.insn(id_insn1),.kind(kind),.imm(imm),.use1(use1),.use2(use2),.write_rd(wr),.serial(serial),.illegal(illegal),
 .control(control),.rs1(a),.rs2(b),.rd(dummy),.csr_exists(1'b0),.csr_writable(1'b0));
 integer op,f3,f7,checked=0,all_cases=0;
 initial begin
  for(op=0;op<128;op=op+1) for(f3=0;f3<8;f3=f3+1) for(f7=0;f7<128;f7=f7+1) begin
   id_insn1=(f7<<25)|(17<<20)|(5<<15)|(f3<<12)|(3<<7)|op;#1;
   if(kind==0 && !illegal && !serial) begin
    if(id1_imm!==imm || id1_control!==control || id1_wr!==wr || rs1_1!==a || rs2_1!==b || rd1!==dummy) $fatal(1,"Lane1 decode mismatch %h",id_insn1);
    checked=checked+1;
   end
   all_cases=all_cases+1;
  end
  $display("PASS lane1 ALU decode inputs=%0d admitted=%0d",all_cases,checked);$finish;
 end
endmodule
''')
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';decoder=ROOT/'hardware/pds/source/core/nc_decode.v'
 for cmd,name in (([iv,'-g2012','-s','lane1_decode_tb','-o',out/'unit.vvp',decoder,tb],'compile.log'),([iv.with_name('vvp.exe'),out/'unit.vvp'],'unit.log')):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(out/name).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(name,p.stdout+p.stderr)
 text=(out/'unit.log').read_text();assert 'PASS lane1 ALU decode inputs=131072' in text
 files=[Path(__file__).resolve(),core,tb,decoder];result=dict(status='PASS',tests=[text.strip()],input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(text.strip())
if __name__=='__main__':main()
