"""Directed dual branch/MUL, slot identities, precise exceptions and live traces."""
from pathlib import Path
import argparse,json,hashlib,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'simulation/scripts/run'));import regression
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);out=src/'pair_checks';out.mkdir(exist_ok=True)
 g=json.loads((src/'generation.json').read_text());inputs=[Path(__file__).resolve()]
 for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
 rtl=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[])
 actual=[src/p.name if str(p.relative_to(ROOT)) in g['override_sha256'] else p for p in rtl];model=src/'pango_ram_wide_models.v';inputs+=actual+[model]
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
 def run(cmd,log):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(out/log).write_bytes(p.stdout+p.stderr)
  assert p.returncode==0,(log,p.stdout[-3000:]);return p.stdout.decode(errors='replace')
 gcc=regression.find('riscv-none-elf-gcc',Path('D:/Program Files/riscv').glob('**/riscv-none-elf-gcc.exe'));images={}
 for name in (('pair_joint','pair_precise')):
  source=ROOT/f'simulation/research/{"dual_joint" if name=="pair_joint" else "dual_types"}/{name}.S';old=regression.OUT;regression.OUT=out
  try:images[name]=regression.build(gcc,source,name)
  finally:regression.OUT=old
  inputs +=[source,images[name][0]]
 for kind in ('core','soc'):
  cpu='dut' if kind=='core' else 'dut.cpu';bench=src/'checks'/(kind+'_tb.v');s=bench.read_text();inputs+=[bench]
  block=r'''
 integer qt_branch=0,qt_mul=0,qt_taken=0,qt_not_taken=0,qt_side_broadcast=0,qt_cross=0,qt_pop2=0;
 reg[31:0] qt_next;
 always @(posedge clk) if(rst_n) begin
  if(CPU.pair_issue && CPU.id_pair_flags[9] && (!CPU.id_pair_flags[3] || CPU.second_dep)) $fatal(1,"Unsafe extended pair admission");
  if(CPU.commit1 && CPU.w1_branch) begin
   qt_branch=qt_branch+1;
   if(CPU.w1_insn[6:0]!=7'h63 || CPU.w1_rd!=0) $fatal(1,"Compact branch opcode/write identity");
   qt_next=CPU.w1_result;
  end
  if(CPU.commit1 && CPU.w1_insn[6:0]==7'h33 && CPU.w1_insn[31:25]==1) qt_mul=qt_mul+1;
  if(CPU.ex_fire && CPU.side_execute && CPU.side_branch) begin
   if(CPU.side_taken) qt_taken=qt_taken+1;else qt_not_taken=qt_not_taken+1;
  end
  MUL_CHECK
  SLIDE_CHECK
 end
 always @(negedge clk) if(finish_count==1) $display("PAIR_COVER branch=%0d mul=%0d taken=%0d not_taken=%0d side_broadcast=%0d cross=%0d pop2=%0d",qt_branch,qt_mul,qt_taken,qt_not_taken,qt_side_broadcast,qt_cross,qt_pop2);
'''
  if a.variant!='dual_types_branch':
   block=block.replace('MUL_CHECK',r'''if(CPU.m_valid && CPU.m_lane) qt_side_broadcast=qt_side_broadcast+1;
   if(CPU.memory.valid && CPU.memory.side_packet[64] && CPU.memory.secondary_multiply !== (CPU.memory.side_packet[38:32]==7'h33 && CPU.memory.side_packet[63:57]==1 && !CPU.memory.side_packet[46])) $fatal(1,"Compact MUL decode mismatch");''')
  else:block=block.replace('MUL_CHECK','')
  block=block.replace('SLIDE_CHECK', 'if(CPU.pair_issue && CPU.fetch.cross_window) qt_cross=qt_cross+1;if(CPU.fetch.pop_two_groups) qt_pop2=qt_pop2+1;' if a.variant.startswith('dual_joint_') else '')
  target=out/(kind+'_tb.v');target.write_text(s.replace('endmodule',block.replace('CPU',cpu)+'\nendmodule'));inputs+=[target]
  files=[p for p in actual if p.name in {q.name for q in (ROOT/'hardware/pds/source/core').glob('*.v')}] if kind=='core' else actual+[model]
  run([iv,'-g2012','-s',kind+'_tb','-o',out/(kind+'.vvp'),*files,target],kind+'_compile.log')
 tests=[];coverage=[]
 for name,(image,data) in images.items():
  for kind,seeds in (('core',(37,613)),('soc',(0,))):
   for seed in seeds:
    trace=out/f'{name}_{kind}_{seed}.trace';s=run([vvp,out/(kind+'.vvp'),f'+image={image}',f'+trace={trace}',f'+seed={seed}',f'+uart={out}/unused_uart.txt'],f'{name}_{kind}_{seed}.log')
    assert 'PASS cycles=' in s,s[-3000:];m=re.search(r'PAIR_COVER ([^\r\n]+)',s);assert m
    c={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])};coverage.append(dict(program=name,kind=kind,seed=seed,**c))
    if name!='pair_precise':
     regression.differential(data,trace)
     if kind=='soc':
      if a.variant!='dual_types_mul':assert c['branch']>=8 and c['taken']>=4 and c['not_taken']>=4,c
      if a.variant!='dual_types_branch':assert c['mul']>=16 and c['side_broadcast']>=16,c
      if a.variant.startswith('dual_joint_'):assert c['cross']>=16 and c['pop2']>=1,c
    else:
     causes=[int(line.split()[-1],16) for line in trace.read_text().splitlines() if line.split()[4]=='1'];assert causes==[0,5],causes
    tests +=[f'{name} {kind} seed={seed} PASS']
 x=dict(status='PASS',tests=tests,coverage=coverage,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs},override_sha256=g['override_sha256'])
 (out/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({k:v for k,v in x.items() if k not in ('input_sha256','override_sha256')},indent=2))
if __name__=='__main__':main()
