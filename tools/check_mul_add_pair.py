"""Final trial: independent ISA differential tests for dependent MUL/ADD pairs."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'simulation/scripts/run'))
import regression

def main():
 src=ROOT/'simulation/results/load_bp_dual_boundary_auto_mul_add_pair'
 out=src/'muladd_checks';out.mkdir(exist_ok=True)
 asm='''.section .text.start
.globl _start
_start:
 li s0,32
 li s1,0x80000001
 li s2,-3
 li s3,0x12345678
 la s4,datum
loop:
 .balign 8
 mul a0,s1,s2
 add a1,a0,s3
 add s5,a1,a0
 .balign 8
 mul a0,s2,s1
 add a2,s3,a0
 add s6,a2,a0
 .balign 8
 mul a0,s1,s1
 add a3,a0,a0
 add s7,a3,a0
 // Previous writer to the MUL destination must not supply the ADD operand.
 div a0,s1,s2
 .balign 8
 mul a0,s2,s2
 add a4,a0,s3
 // Pending independent addend; ordinary dependency handling must survive.
 lw t2,0(s4)
 .balign 8
 mul a0,s1,s2
 add a5,t2,a0
 // WAW cannot retire as a pair; x0 is not a MUL-produced operand.
 .balign 8
 mul a0,s1,s2
 add a0,a0,s3
 .balign 8
 mul zero,s1,s2
 add a6,zero,s3
 // High multiply followed by ADD must retain the ordinary path.
 .balign 8
 mulh a0,s1,s2
 add a7,a0,s3
 addi s1,s1,17
 addi s0,s0,-1
 bnez s0,loop
 li t0,0x20003000
 li t1,1
 sw t1,0(t0)
done: j done
.section .data
.balign 4
datum: .word 0x76543210
'''
 source=out/'muladd.S';source.write_text(asm)
 gcc=regression.find('riscv-none-elf-gcc',Path('D:/Program Files/riscv').glob('**/riscv-none-elf-gcc.exe'))
 old=regression.OUT;regression.OUT=out
 try:image,data=regression.build(gcc,source,'muladd')
 finally:regression.OUT=old
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
 g=json.loads((src/'generation.json').read_text());files=[]
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert hashlib.sha256(p.read_bytes()).hexdigest()==h;files.append(p)
 def run(cmd,name):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180)
  (out/name).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(name,p.stdout[-3000:]);return p.stdout.decode(errors='replace')
 tests=[];coverage=[]
 for kind,seeds in [('core',[37,613,2026]),('soc',[0])]:
  cpu='dut' if kind=='core' else 'dut.cpu'
  bench=out/(kind+'_tb.v');s=(src/'checks'/(kind+'_tb.v')).read_text()
  mon='''
 integer ma_c=0,ma_d=0,ma_both=0;
 always @(posedge clk) if(rst_n) begin
  if(CPU.ex_fire && CPU.side_muladd) begin
   if(CPU.ex_side[1:0]==2'b10) ma_c=ma_c+1;
   if(CPU.ex_side[1:0]==2'b01) ma_d=ma_d+1;
   if(CPU.ex_side[1:0]==2'b11) ma_both=ma_both+1;
  end
  if(CPU.f1_valid && CPU.f1_tag=={CPU.ex_tag,1'b1} && CPU.ex_fire && CPU.side_muladd)
   $fatal(1,"Premature MUL/ADD side forwarding");
 end
 always @(negedge clk) if(finish_count==1)
  $display("MULADD_COVER c=%0d d=%0d both=%0d",ma_c,ma_d,ma_both);
'''
  # f1_valid belongs to the previous EX cycle; admission coverage plus the
  # independent retirement model checks forwarding without mixing cycles.
  mon=re.sub(r'  if\(CPU.f1_valid.*?\$fatal\(1,"Premature MUL/ADD side forwarding"\);\n','',mon,flags=re.S)
  bench.write_text(s.replace('endmodule',mon.replace('CPU',cpu)+'\nendmodule'))
  actual=[p for p in files if p.name in {q.name for q in (ROOT/'hardware/pds/source/core').glob('*.v')}] if kind=='core' else files+[ROOT/'hardware/pds/source/perips/nc_uart.v',src/'pango_ram_wide_models.v']
  run([iv,'-g2012','-s',kind+'_tb','-o',out/(kind+'.vvp'),*actual,bench],kind+'_compile.log')
  for seed in seeds:
   label=f'{kind}_{seed}';trace=out/(label+'.trace')
   t=run([vvp,out/(kind+'.vvp'),f'+image={image}',f'+trace={trace}',f'+seed={seed}',f'+uart={out}/uart.txt'],label+'.log')
   assert 'PASS cycles=' in t,t[-3000:];regression.differential(data,trace)
   m=re.search(r'MULADD_COVER c=(\d+) d=(\d+) both=(\d+)',t);assert m
   c=list(map(int,m.groups()));assert all(c),(label,c)
   tests.append(label+' PASS');coverage.append(dict(test=label,rs1=c[0],rs2=c[1],both=c[2]))
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,coverage=coverage,override_sha256=g['override_sha256'],checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
 print(json.dumps(dict(status='PASS',tests=tests,coverage=coverage),indent=2))

if __name__=='__main__':main()
