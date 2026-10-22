"""Local RAM ownership, prefix faults, registered result buses and admission proofs."""
from pathlib import Path
import argparse,json,hashlib,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);ap.add_argument('--mode',choices=('extra','pairs','bus','directed','operands','audit','stats'),required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);g=json.loads((src/'generation.json').read_text());out=src/(a.mode+'_checks');out.mkdir(exist_ok=True)
 for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
 inputs=[Path(__file__).resolve()];iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
 def run(cmd,log,timeout=180):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=timeout);(out/log).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(log,(p.stdout+p.stderr)[-3500:]);return p.stdout.decode(errors='replace')
 if a.mode in ('extra','pairs'):
  base=ROOT/('tools/check_dual_native_extra.py' if a.mode=='extra' else 'tools/check_dual_joint_pairs.py');s=base.read_text();inputs.append(base)
  if a.mode=='extra':s=s.replace('f.classify(inst1)','f.classify_side(inst1)').replace('[105:74]','[106:75]')
  else:
   s=s.replace('CPU.id_pair_flags[9] && (!CPU.id_pair_flags[3]', 'CPU.id_pair_flags[9] && CPU.id_side_kind!=4 && CPU.id_side_kind!=5 && (!CPU.id_pair_flags[3]')
   s=s.replace('CPU.memory.side_packet[64]','CPU.memory.side_packet[96]').replace('CPU.memory.side_packet[38:32]','CPU.memory.side_packet[70:64]').replace('CPU.memory.side_packet[63:57]','CPU.memory.side_packet[95:89]').replace('CPU.memory.side_packet[46]','CPU.memory.side_packet[78]')
  ns={'__file__':str(base),'__name__':'lsu_checks'};exec(compile(s,str(base),'exec'),ns)
  if a.mode=='extra':ns['OUT']=src;sys.argv=[str(base)]
  else:sys.argv=[str(base),'--variant',a.variant]
  ns['main']();p=src/('dual_checks' if a.mode=='extra' else 'pair_checks')/'result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__));save(p,x);return
 files=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[]);files=[src/p.name if str(p.relative_to(ROOT)) in g['override_sha256'] else p for p in files];model=src/'pango_ram_wide_models.v';tests=[];coverage=[]
 if a.mode=='bus':
  tb=ROOT/'simulation/research/dual_lsu/bus_tb.v';rtl=[src/'nc_local_bus.v',ROOT/'hardware/pds/source/perips/nc_uart.v',model,tb];inputs+=rtl
  mode=0 if a.variant=='dual_lsu_shared' else 1
  run([iv,'-g2012','-s','lsu_bus_tb',f'-Plsu_bus_tb.SECOND_PORT={mode}','-o',out/'sim.vvp',*rtl],'compile.log')
  for seed in (17,91,2026):
   t=run([vvp,out/'sim.vvp',f'+seed={seed}'],f'seed_{seed}.log');assert 'PASS LSU bus cycles=30000' in t,t;tests.append(t.strip())
 elif a.mode=='directed':
  sys.path.insert(0,str(ROOT/'simulation/scripts/run'));import regression
  gcc=regression.find('riscv-none-elf-gcc',Path('D:/Program Files/riscv').glob('**/riscv-none-elf-gcc.exe'));source=ROOT/'simulation/research/dual_lsu/pair_lsu.S';old=regression.OUT;regression.OUT=out
  try:image,data=regression.build(gcc,source,'pair_lsu')
  finally:regression.OUT=old
  inputs +=[source,image]
  for kind in ('core','soc'):
   cpu='dut' if kind=='core' else 'dut.cpu';original=src/'checks'/(kind+'_tb.v');s=original.read_text();inputs.append(original)
   mon='''
 integer lc_load=0,lc_store=0,lc_pairmem=0,lc_dual=0,lc_replay=0,lc_fault_pairs=0,lc_early0=0,lc_early1=0;
 reg[31:0] lc_sentinel=32'h7e6d5c4b;
 always @(posedge clk) if(rst_n) begin
  if(CPU.commit1 && CPU.w1_load) lc_load=lc_load+1;
  if(CPU.commit1 && CPU.w1_store) lc_store=lc_store+1;
  if(CPU.pair_issue && (CPU.id_side_kind==4 || CPU.id_side_kind==5)) begin
   lc_pairmem=lc_pairmem+1;
   if(CPU.id_kind==4 && CPU.a==32'h30000000) lc_fault_pairs=lc_fault_pairs+1;
  end
  if(CPU.d_req_valid && CPU.d_req_ready && CPU.s_req_valid && CPU.s_req_ready) lc_dual=lc_dual+1;
  if(CPU.side_replay) lc_replay=lc_replay+1;
  FORWARD_COVER
 end
 always @(negedge clk) if(finish_count==1) $display("LSU_DIRECTED load=%0d store=%0d memory_pairs=%0d dual=%0d replay=%0d fault_pairs=%0d early0=%0d early1=%0d",lc_load,lc_store,lc_pairmem,lc_dual,lc_replay,lc_fault_pairs,lc_early0,lc_early1);
'''
   if a.variant in ('dual_lsu_forward','dual_lsu_pair'):
    mon=mon.replace('FORWARD_COVER',"if(CPU.l0_valid && !(CPU.commit && CPU.w_tag==CPU.l_tag)) lc_early0=lc_early0+1;\n  if(CPU.l1_valid && !(CPU.commit1 && CPU.w_tag==CPU.l_tag)) lc_early1=lc_early1+1;\n  if(CPU.l0_valid && CPU.commit && CPU.w_tag==CPU.l_tag && CPU.l0_data!==CPU.w_result) $fatal(1,\"Registered primary completion differs from WB\");\n  if(CPU.l1_valid && CPU.commit1 && CPU.w_tag==CPU.l_tag && CPU.l1_data!==CPU.w1_result) $fatal(1,\"Registered secondary completion differs from WB\");")
   else:mon=mon.replace('FORWARD_COVER','')
   tb=out/(kind+'_tb.v');tb.write_text(s.replace('endmodule',mon.replace('CPU',cpu)+'\nendmodule'));rtl=[p for p in files if p.name in {q.name for q in (ROOT/'hardware/pds/source/core').glob('*.v')}] if kind=='core' else files+[model];inputs +=rtl+[tb]
   run([iv,'-g2012','-s',kind+'_tb','-o',out/(kind+'.vvp'),*rtl,tb],kind+'_compile.log')
   for seed in ((37,613) if kind=='core' else (0,)):
    trace=out/f'{kind}_{seed}.trace';t=run([vvp,out/(kind+'.vvp'),f'+image={image}',f'+trace={trace}',f'+seed={seed}',f'+uart={out}/unused.txt'],f'{kind}_{seed}.log');assert 'PASS cycles=' in t,t[-2000:]
    causes=[int(line.split()[-1],16) for line in trace.read_text().splitlines() if line.split()[4]=='1'];assert causes==[5,5,5,4,7],causes
    m=re.search(r'LSU_DIRECTED ([^\r\n]+)',t);assert m;c={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])};coverage.append(dict(kind=kind,seed=seed,**c))
    if kind=='soc':assert c['load']>=32 and c['store']>=32 and c['replay']>=3 and c['fault_pairs']>=2,c
    tests.append(f'{kind} ordered RAM/subword/alias/primary fault/secondary replay seed={seed} PASS')
 elif a.mode=='stats':
  tb=out/'stats_tb.v';tb.write_text('''`timescale 1ns/1ps
module stats_tb;
 reg clk=0;always #5 clk=~clk;reg rst_n=0,control=0;reg[31:0] control_data=0;reg[15:0] events=0;
 nc_stats s(.clk(clk),.rst_n(rst_n),.control(control),.control_data(control_data),.events(events),.addr(4'd11),.data());
 initial begin
 repeat(3) @(negedge clk);rst_n=1;control=1;control_data=3;
 @(negedge clk);control=0;events=(1<<0)|(1<<8)|(1<<9)|(1<<10)|(1<<14);
 repeat(100) @(negedge clk);control=1;control_data=0;events=0;
 @(negedge clk);control=0;
 if(s.counters[11]!=200 || s.counters[9]!=200 || s.counters[1]!=100) $fatal(1,"Two-load count failed");
 control=1;control_data=3;@(negedge clk);control=0;events=(1<<14)|(1<<15);
 repeat(100) @(negedge clk);control=1;control_data=0;events=0;@(negedge clk);control=0;
 if(s.counters[11]!=100 || s.counters[12]!=100) $fatal(1,"Side-only event lost");
 control=1;control_data=3;@(negedge clk);control=0;events=(1<<11)|(1<<15);s.counters[12]=32'hfffffffe;
 repeat(2) @(negedge clk);control=1;control_data=0;events=0;@(negedge clk);control=0;
 if(s.counters[12]!=2 || !s.overflow[11]) $fatal(1,"Dual-store overflow failed");
 $display("PASS double-load, side-only memory events and dual-store overflow");$finish;end
endmodule
''');inputs +=[tb,src/'nc_stats.v'];run([iv,'-g2012','-s','stats_tb','-o',out/'sim.vvp',src/'nc_stats.v',tb],'compile.log');t=run([vvp,out/'sim.vvp'],'simulation.log');assert 'PASS double-load' in t;tests.append(t.strip())
 elif a.mode=='audit':
  def linux(p):p=Path(p).resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
  inputs+=files+[model];t=run(['wsl.exe','-d','Ubuntu','--','verilator','--lint-only','-Wall','-Wno-fatal','--top-module','nc_soc',*[linux(p) for p in files+[model]]],'lint.log');bad=set(re.findall(r'%Warning-(\w+):',t)).intersection({'LATCH','UNOPTFLAT','MULTIDRIVEN','UNDRIVEN','IMPLICIT','PINMISSING','PINNOTFOUND'});assert not bad,bad
  tests.append('PASS no dangerous lint diagnostics')
  fetch=(src/'nc_fetch.v').read_text();fun=fetch[fetch.index(' function[8:0] classify_parts'):];fun=fun[:fun.index(' endfunction')+len(' endfunction')];q=out/'side_proof.v'
  q.write_text('module side_proof(input[31:0] insn,output equal);\n'+fun+'''
 wire[8:0] p=classify_parts(insn);wire allowed=|p[5:3] || p[8];wire[3:0] kind;wire illegal,wr,u1,u2,serial;
 nc_decode d(.insn(insn),.kind(kind),.imm(),.use1(u1),.use2(u2),.write_rd(wr),.serial(serial),.illegal(illegal),.control(),.rs1(),.rs2(),.rd(),.csr_exists(1'b0),.csr_writable(1'b0));
 assign equal=!allowed || (!illegal && !serial && wr==p[2] && u1==p[0] && u2==p[1] && ((kind==1)==insn[6]) && (kind==0 || kind==1 || kind==4 || kind==5 || (kind==6 && !insn[14])));
 endmodule
''');dec=ROOT/'hardware/pds/source/core/nc_decode.v';inputs +=[q,dec];t=run(['wsl.exe','-d','Ubuntu','--','yosys','-p',f'read_verilog -sv {linux(dec)} {linux(q)}; prep -top side_proof -flatten; sat -verify -prove equal 1'],'side_sat.log');assert 'SUCCESS!' in t;tests.append('PASS SAT all side ALU/branch/MUL/load/store source/write/class flags equal full decoder')
  core=(src/'nc_core.v').read_text();mem=(src/'nc_memory.v').read_text();assert '.WIDTH(281),.DEPTH(4)' in core and 'side_replay' in core and 'side_bad' in core
  assert 'output wire return_valid' not in mem and 'return_data=rsp_data' not in mem
  tests +=['PASS registered EX/MEM credit boundary preserved; no EX early RAM request or raw RAM-to-EX return','PASS memory-only secondary port, EX fallback for alignment/MMIO/range and physical 64-bit-line alias serialization']
 else:
  if a.variant in ('dual_lsu_shared','dual_lsu_ports'):
   parent=ROOT/'simulation/results/load_bp_dual_legacy_fifo';assert sha(src/'nc_operands.v')==sha(parent/'nc_operands.v');e=json.loads((parent/'operand_checks/result.json').read_text());tests=['PASS shared exact-hash 300000-cycle five-source operand equivalence'];inputs +=[parent/'operand_checks/result.json',src/'nc_operands.v']
  else:
   actual=src/'nc_operands.v';old=ROOT/'simulation/results/load_bp_dual_legacy_return/operands_checks';header=actual.read_text().split(' reg[223:0] side')[0].replace('module nc_operands(','module old_nc_operands(');body=(old/'reference.v').read_text().split(' reg[203:0] packets')[1];body=' reg[203:0] packets'+body
   body=body.replace('[5:0]','[6:0]').replace('[23:0]','[27:0]').replace('[191:0]','[223:0]').replace('k<6','k<7').replace('m_valid,r_valid,w_valid','m_valid,l0_valid,l1_valid,w_valid').replace('m_tag,r_tag,w_tag','m_tag,l0_tag,l1_tag,w_tag').replace('m_data,r_data,w_data','m_data,l0_data,l1_data,w_data')
   ref=out/'reference.v';ref.write_text(header+body);original=ROOT/'simulation/research/dual_native/operands_tb.v';s=original.read_text().replace('.next_f_tag(next_f_tag),.next_m_tag(next_m_tag),.next_w_tag(next_w_tag),','')
   s=s.replace(' reg wait_a=0,',' reg l0_valid=0,l1_valid=0;reg[3:0] l0_tag=0,l1_tag=0;reg[31:0] l0_data=0,l1_data=0;\n reg wait_a=0,')
   s=s.replace('  .w_valid(w_valid)','  .l0_valid(l0_valid),.l1_valid(l1_valid),.l0_tag(l0_tag),.l1_tag(l1_tag),.l0_data(l0_data),.l1_data(l1_data),.w_valid(w_valid)')
   s=s.replace('   #1;compare;',"   rng=step(rng);l0_valid=rng[0];l1_valid=rng[1];l0_tag=rng[5:2];l1_tag=rng[9:6];l0_data=rng;\n   rng=step(rng);l1_data=rng;\n   if(i%5==0) begin l0_valid=1;l0_tag=tag_c;l1_valid=1;l1_tag=tag_d;end\n   #1;compare;")
   tb=out/'operands_tb.v';tb.write_text(s);inputs +=[actual,ref,tb,old/'reference.v',original];run([iv,'-g2012','-s','operands_equivalence_tb','-o',out/'sim.vvp',actual,ref,tb],'compile.log')
   for seed in (17,91,2026):
    t=run([vvp,out/'sim.vvp',f'+seed={seed}'],f'seed_{seed}.log');assert 'PASS operands equivalence cycles=100000' in t;tests.append(t.strip())
 save(out/'result.json',dict(status='PASS',variant=a.variant,tests=tests,coverage=coverage,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}));print(a.mode,'PASS',a.variant,len(tests))
if __name__=='__main__':main()
