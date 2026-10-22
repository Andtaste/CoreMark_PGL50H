"""Compile/run isolated dual-issue RTL with independently counted retire slots."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'simulation/results/load_bp_dual_issue'
sys.path.insert(0,str(ROOT/'simulation/scripts/run'));import regression
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def linux(p):
 p=Path(p).resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def prepare_benches(dest):
 core=(ROOT/'simulation/tb/core_tb.v').read_text().replace('reg[1023:0]','reg[4095:0]')
 core=rep(core,'wire[31:0] ia,da,dw,idata,ddata;', 'wire[63:0] idata;wire[31:0] ia,da,dw,ddata;')
 core=rep(core,'reg[31:0] iq=0,dq=0;', 'reg[63:0] iq=0;reg[31:0] dq=0;')
 core=rep(core,'iq<=index(ia)<0 ? 0 : mem[index(ia)];',
  "iq<=index(ia)<0 ? 0 : {mem[index({ia[31:3],3'b100})],mem[index({ia[31:3],3'b000})]};")
 core=rep(core,'  if(finish_count!=0) begin', '''  if(dut.trace1_valid) begin
   if(!tv || tt) $fatal(1,"Secondary retired without clean primary");
   $fdisplay(fd,"%08x %08x %d %08x 0 00000000",dut.trace1_pc,dut.trace1_insn,dut.trace1_rd,dut.trace1_data);
   retired<=retired+2;
  end
  if(finish_count!=0) begin''')
 soc=(ROOT/'simulation/tb/soc_tb.v').read_text().replace('reg[1023:0]','reg[4095:0]')
 soc=rep(soc,'ref_retired=ref_retired+1;', 'ref_retired=ref_retired+(dut.cpu.commit1 ? 2 : 1);')
 soc=rep(soc,'  if(tohost!=0 && finish_count==0) begin', '''  if(dut.cpu.trace1_valid) begin
   if(!dut.cpu.trace_valid || dut.cpu.trace_trap) $fatal(1,"Secondary retired without clean primary");
   retired<=retired+2;
   if(!notrace) $fdisplay(fd,"%08x %08x %d %08x 0 00000000",dut.cpu.trace1_pc,dut.cpu.trace1_insn,dut.cpu.trace1_rd,dut.cpu.trace1_data);
  end
  if(tohost!=0 && finish_count==0) begin''')
 coverage='''
 integer pair_issued=0,pair_executed=0,pair_retired=0,pair_squashed_fault=0,dual_streak=0,max_dual_streak=0;
 integer structural=0,dependency_blocked=0,single_issued=0;
 integer win_pairs=0,win_issued=0,win_dep_blocked=0;
 reg check_secondary=0;integer ref_secondary=0;
 always @(posedge clk) if(rst_n) begin
  if(CPU.wb_valid && (!CPU.live[CPU.w_tag] || CPU.head!=CPU.w_tag)) $fatal(1,"Retirement group out of order");
  if(CPU.issue) begin
   if(CPU.pair_issue) pair_issued=pair_issued+1;else single_issued=single_issued+1;
   if(CPU.id_second) structural=structural+1;
   if(CPU.id_second && CPU.second_dep) dependency_blocked=dependency_blocked+1;
  end
  if(CPU.ex_fire && CPU.side_execute) pair_executed=pair_executed+1;
  if(CPU.do_trap && CPU.w_side[101]) pair_squashed_fault=pair_squashed_fault+1;
  if(CPU.commit1) begin
   pair_retired=pair_retired+1;dual_streak=dual_streak+1;
   if(dual_streak>max_dual_streak) max_dual_streak=dual_streak;
   if(!CPU.commit || CPU.w1_pc!=CPU.w_pc+4 || CPU.w_kind==1 || CPU.w_kind==2 || CPU.w_kind==3) $fatal(1,"Invalid pair retirement");
   if(CPU.w_wr && CPU.w_rd!=0 && CPU.w_rd==CPU.w1_rd) $fatal(1,"RF WAW pair");
  end else dual_streak=0;
  check_secondary=0;
  if(CPU.csr.stats.control) begin
   if(CPU.csr.stats.control_data[1]) begin ref_secondary=0;win_pairs=0;win_issued=0;win_dep_blocked=0;end
   else if(!CPU.csr.stats.control_data[0]) check_secondary=1;
  end else if(CPU.csr.stats.enabled) begin
   if(CPU.commit1) ref_secondary=ref_secondary+1;
   if(CPU.issue) begin
    win_issued=win_issued+1;
    if(CPU.pair_issue) win_pairs=win_pairs+1;
    if(CPU.id_second && CPU.second_dep) win_dep_blocked=win_dep_blocked+1;
   end
  end
 end
 always @(negedge clk) if(check_secondary) begin
  if(CPU.csr.stats.counters[10]!=ref_secondary) $fatal(1,"Secondary/reference stats mismatch");
  $display("DUAL_WINDOW secondary_retired=%0d pairs_issued=%0d groups_issued=%0d dependency_blocked=%0d",ref_secondary,win_pairs,win_issued,win_dep_blocked);
 end
 always @(negedge clk) if(finish_count==1) $display("DUAL_STATS issued=%0d executed=%0d retired=%0d fault_cancelled=%0d max_dual_streak=%0d second_visible=%0d dependency_blocked=%0d singles=%0d",pair_issued,pair_executed,pair_retired,pair_squashed_fault,max_dual_streak,structural,dependency_blocked,single_issued);
'''
 for name,s,cpu in (('core_tb',core,'dut'),('soc_tb',soc,'dut.cpu')):
  s=rep(s,'endmodule',coverage.replace('CPU',cpu)+'\nendmodule');(dest/(name+'.v')).write_text(s)
 return dest/'core_tb.v',dest/'soc_tb.v'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=('smoke','checks','performance','validation'),required=True);a=ap.parse_args()
 dest=OUT/a.phase;dest.mkdir(exist_ok=True)
 meta=json.loads((OUT/'generation.json').read_text());override=meta['override_sha256']
 accepted=ROOT/'docs/accepted_baseline.json';sta=ROOT/'hardware/pds/report_timing/top.rtr';guard={p:sha(p) for p in (accepted,sta)}
 b=json.loads(accepted.read_text());assert sha(accepted)==meta['baseline_sha256']
 for n,h in b['source_sha256'].items():assert sha(ROOT/n)==h,n
 for n,h in override.items():assert sha(OUT/Path(n).name)==h,n
 rtl=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[])
 actual=[OUT/p.name if str(p.relative_to(ROOT)) in override else p for p in rtl]
 core_tb,soc_tb=prepare_benches(dest);model=ROOT/'simulation/models/pango_ram_models.v'
 inputs=rtl+[model,ROOT/'simulation/tb/core_tb.v',ROOT/'simulation/tb/soc_tb.v',Path(__file__).resolve(),ROOT/'tools/generate_dual_issue.py',ROOT/'simulation/research/dual_issue/nc_fetch.v',ROOT/'simulation/research/dual_issue/nc_regfile.v']
 logs=[]
 def run(cmd,name,timeout=240):
  with (dest/name).open('wb') as f:x=subprocess.run(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
  t=(dest/name).read_text(errors='replace');assert x.returncode==0,(name,t[-5000:]);return t
 if a.phase in ('performance','validation'):
  uart_src=ROOT/'hardware/pds/source/perips/nc_uart.v';uart=dest/'nc_uart_sim.v';uart.write_text(uart_src.read_text().replace('BAUD=115200','BAUD=9375000'))
  soc_tb.write_text(soc_tb.read_text().replace(' defparam dut.bus.uart.BAUD=9375000;',''))
  actual=[uart if p==uart_src else p for p in actual]
  prefix=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--']
  run([*prefix,'verilator','--binary','--timing','-j','4','-Wno-fatal','-DCOREMARK_SIM','--top-module','soc_tb','--Mdir',linux(dest/'obj'),*[linux(p) for p in actual+[model,soc_tb]]],'compile.log',600)
  image=ROOT/('sw/build/coremark_validation_1/coremark.hex' if a.phase=='validation' else 'sw/build/coremark_performance_10/coremark.hex');inputs+=[image]
  text=run([*prefix,linux(dest/'obj/Vsoc_tb'),f'+image={linux(image)}',f'+trace={linux(dest)}/unused.trace',f'+uart={linux(dest)}/uart.txt','+notrace=1','+limit=33000000'],'simulation.log',600)
  u=(dest/'uart.txt').read_text();assert 'COUNTER_CHECK_PASS' in text and 'CRC validation   : PASS' in u and 'PASS cycles=' in text
  metrics={s.split(':',1)[0].strip():s.split(':',1)[1].strip() for s in u.splitlines() if ':' in s}
  ref=json.loads((ROOT/('simulation/results/coremark_validation_1_verilator_exid_final/result.json' if a.phase=='validation' else 'simulation/results/coremark_performance_10_verilator_exid_aux/result.json')).read_text())
  for k in ('Retired instructions','Retired loads','Retired stores','BJP instructions','seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal'):assert metrics[k]==ref['metrics'][k],k
  result=dict(status='PASS',variant='dual_issue',scope='Isolated aligned limited dual-issue; production unchanged; not adopted',metrics=metrics,override_sha256=override,image_sha256=sha(image))
  for name,marker in (('predictor','PREDICTOR_STATS'),('multiply','MULTIPLY_STATS'),('dual','DUAL_WINDOW')):
   m=re.search(marker+r' ([^\r\n]+)',text);assert m;result[name]={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])}
 else:
  iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
  core_rtl=[p for p in actual if p.name in {q.name for q in (ROOT/'hardware/pds/source/core').glob('*.v')}]
  run([iv,'-g2012','-s','core_tb','-o',dest/'core.vvp',*core_rtl,core_tb],'core_compile.log')
  run([iv,'-g2012','-s','soc_tb','-o',dest/'soc.vvp',*actual,model,soc_tb],'soc_compile.log')
  names=('directed','random_17','random_91','random_2026','prediction') if a.phase=='checks' else ('random_17',)
  for name in names:
   image=ROOT/f'simulation/results/{name}.hex';binary=image.with_suffix('.bin');inputs+=[image,binary];data=binary.read_bytes();data+=bytes(65536-len(data))
   for seed in ((37,613) if a.phase=='checks' else (37,)):
    trace=dest/f'{name}_{seed}.trace';t=run([vvp,dest/'core.vvp',f'+image={image}',f'+trace={trace}',f'+seed={seed}'],f'{name}_{seed}.log');assert 'PASS cycles=' in t
    if name=='directed':
     causes=[int(s.split()[-1],16) for s in trace.read_text().splitlines() if s.split()[4]=='1'];assert causes==[4,6,5,7,2,11,2,0,0x80000003,0x80000007,0x8000000b] or causes==[4,6,5,7,2,11,2,0x80000003,0x80000007,0x8000000b],causes
    else:regression.differential(data,trace)
    logs.append(f'core {name} seed={seed} PASS')
  for name in (('prediction','throughput','soc_faults','random_17','random_91','random_2026') if a.phase=='checks' else ('random_17',)):
   image=ROOT/f'simulation/results/{name}.hex';binary=image.with_suffix('.bin');inputs+=[image,binary];data=binary.read_bytes();data+=bytes(65536-len(data));trace=dest/f'soc_{name}.trace'
   t=run([vvp,dest/'soc.vvp',f'+image={image}',f'+trace={trace}',f'+uart={dest}/unused_uart.txt'],f'soc_{name}.log');assert 'PASS cycles=' in t
   if name=='soc_faults':
    causes=[int(s.split()[-1],16) for s in trace.read_text().splitlines() if s.split()[4]=='1'];assert causes==[5,0,0,3,1,7,0x80000007],causes
   else:regression.differential(data,trace)
   logs.append('soc '+name+' PASS')
  if a.phase=='checks':
   fixtures=sorted((ROOT/'references/isa/generated').glob('*.bin'));assert len(fixtures)==47
   for fixture in fixtures:
    data=fixture.read_bytes();data+=bytes(65536-len(data));image=dest/'isa.hex';image.write_text(''.join(f'{int.from_bytes(data[i:i+4],"little"):08x}\n' for i in range(0,65536,4)))
    t=run([vvp,dest/'soc.vvp',f'+image={image}',f'+trace={dest}/{fixture.stem}.trace',f'+uart={dest}/unused_uart.txt','+legacy=1','+limit=100000'],fixture.stem+'.log');assert 'PASS cycles=' in t
    inputs+=[fixture];logs.append('isa '+fixture.stem+' PASS')
  result=dict(status='PASS',variant='dual_issue',scope=a.phase,tests=logs,override_sha256=override)
 for p,h in guard.items():assert sha(p)==h,p
 for n,h in b['source_sha256'].items():assert sha(ROOT/n)==h,n
 result['input_sha256']={str(p.relative_to(ROOT)):sha(p) for p in inputs}
 result['actual_compile_sha256']={str(p.relative_to(ROOT)):sha(p) for p in actual+[model,soc_tb,core_tb]}
 save(dest/'result.json',result)
 if a.phase=='performance':save(OUT/'result.json',result)
 print(json.dumps({k:v for k,v in result.items() if k not in ('input_sha256','actual_compile_sha256','override_sha256')},indent=2))
if __name__=='__main__':main()
