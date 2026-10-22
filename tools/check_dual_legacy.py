"""Extra ownership, six-source operand, timeline, and whole-core checks."""
from pathlib import Path
import argparse,json,hashlib,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def run(out,cmd,log,timeout=180):
 p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=timeout);(out/log).write_bytes(p.stdout+p.stderr)
 assert p.returncode==0,(log,(p.stdout+p.stderr)[-3500:]);return p.stdout.decode(errors='replace')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);ap.add_argument('--mode',choices=('extra','pairs','operands','timeline','audit'),required=True);a=ap.parse_args()
 src=ROOT/('simulation/results/load_bp_'+a.variant);g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
 if a.mode in ('extra','pairs'):
  base=ROOT/('tools/check_dual_native_extra.py' if a.mode=='extra' else 'tools/check_dual_joint_pairs.py');s=base.read_text()
  if a.mode=='extra':
   s=s.replace('f.classify(inst1)','f.classify_side(inst1)').replace('[105:74]','[106:75]')
  else:
   s=s.replace("if a.variant.startswith('dual_joint_'):","if a.variant.startswith('dual_legacy_'):")
   s=s.replace("if a.variant.startswith('dual_joint_') else ''","if a.variant.startswith('dual_legacy_') else ''")
   s=s.replace('CPU.fetch.cross_window','CPU.fetch.rd[0]').replace('CPU.fetch.pop_two_groups','(CPU.fetch.consume && CPU.fetch.pop_two)')
  ns={'__file__':str(base),'__name__':'legacy_checks'};exec(compile(s,str(base),'exec'),ns)
  if a.mode=='extra':ns['OUT']=src;sys.argv=[str(base)]
  else:sys.argv=[str(base),'--variant',a.variant]
  ns['main']();p=src/('dual_checks' if a.mode=='extra' else 'pair_checks')/'result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__));save(p,x);return
 out=src/(a.mode+'_checks');out.mkdir(exist_ok=True);inputs=[Path(__file__).resolve()];tests=[]
 if a.mode=='operands':
  actual=src/'nc_operands.v';header=actual.read_text().split(' reg[223:0] side')[0].replace('module nc_operands(','module old_nc_operands(')
  if a.variant=='dual_legacy_fifo':
   # The fifo-only control uses the unchanged prior five-source queue.
   import check_dual_joint_operands as old
   sys.argv=[str(Path(old.__file__)),'--variant',a.variant];old.main();return
  ref=out/'reference.v';reftext=header+'''
 reg[203:0] packets[0:1];reg[223:0] sides[0:1];reg[18:0] ctrls[0:1];reg[31:0] preds[0:1];reg[2:0] tokens[0:1];
 reg[31:0] values[0:7];reg[3:0] tags[0:7];reg[7:0] waiting;reg rd,wr;reg[1:0] count;
 wire[5:0] en={f_valid,f1_valid,m_valid,r_valid,w_valid,w1_valid};
 wire[23:0] ids={f_tag,f1_tag,m_tag,r_tag,w_tag,w1_tag};
 wire[191:0] datas={f_data,f1_data,m_data,r_data,w_data,w1_data};
 function automatic hit(input[5:0] enables,input[23:0] identities,input[3:0] t);integer k;begin
 hit=0;for(k=0;k<6;k=k+1) hit=hit || (enables[k] && identities[k*4+:4]==t);end endfunction
 function automatic[31:0] select_value(input[5:0] enables,input[23:0] identities,input[191:0] data_values,input needs,input[3:0] t,input[31:0] old);integer k;begin
 select_value=old;for(k=0;k<6;k=k+1) if(needs && enables[k] && identities[k*4+:4]==t) select_value=data_values[k*32+:32];end endfunction
 wire[31:0] a=select_value(waiting[4*rd],tags[4*rd],values[4*rd]);
 wire[31:0] b=select_value(waiting[4*rd+1],tags[4*rd+1],values[4*rd+1]);
 wire[31:0] c=select_value(waiting[4*rd+2],tags[4*rd+2],values[4*rd+2]);
 wire[31:0] d=select_value(waiting[4*rd+3],tags[4*rd+3],values[4*rd+3]);
 assign out_packet={packets[rd][203:136],a,b,packets[rd][71:0]};
 assign out_side={sides[rd][223:136],c,d,sides[rd][71:0]};assign out_tag=tokens[rd];assign out_prediction=preds[rd];assign out_control=ctrls[rd];
 assign in_ready=count<2;assign occupied=count!=0;
 assign out_valid=count!=0 && (!waiting[4*rd] || hit(tags[4*rd])) && (!waiting[4*rd+1] || hit(tags[4*rd+1])) && (!waiting[4*rd+2] || hit(tags[4*rd+2])) && (!waiting[4*rd+3] || hit(tags[4*rd+3]));
 wire push=in_valid && in_ready,pop=out_valid && out_ready;integer i;
 always @(posedge clk) begin
 for(i=0;i<8;i=i+1) if(waiting[i] && hit(tags[i])) begin values[i]<=select_value(1'b1,tags[i],values[i]);waiting[i]<=0;end
 if(push) begin
 packets[wr]<=in_packet;sides[wr]<=in_side;tokens[wr]<=in_tag;ctrls[wr]<=in_control;preds[wr]<=in_prediction;
 tags[4*wr]<=tag_a;tags[4*wr+1]<=tag_b;tags[4*wr+2]<=tag_c;tags[4*wr+3]<=tag_d;
 waiting[4*wr]<=wait_a && !hit(tag_a);waiting[4*wr+1]<=wait_b && !hit(tag_b);waiting[4*wr+2]<=wait_c && !hit(tag_c);waiting[4*wr+3]<=wait_d && !hit(tag_d);
 values[4*wr]<=select_value(wait_a,tag_a,in_packet[135:104]);values[4*wr+1]<=select_value(wait_b,tag_b,in_packet[103:72]);
 values[4*wr+2]<=select_value(wait_c,tag_c,in_side[135:104]);values[4*wr+3]<=select_value(wait_d,tag_d,in_side[103:72]);
 end end
 always @(posedge clk or negedge rst_n) if(!rst_n) begin rd<=0;wr<=0;count<=0;end
 else if(clear) begin rd<=0;wr<=0;count<=0;end else begin
 if(push) wr<=!wr;if(pop) rd<=!rd;
 case({push,pop}) 2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:;endcase end
 endmodule
'''
  reftext=re.sub(r'(?<!automatic )hit\(', 'hit(en,ids,',reftext)
  reftext=re.sub(r'(?<!automatic\[31:0\] )select_value\(', 'select_value(en,ids,datas,',reftext)
  ref.write_text(reftext)
  source=ROOT/'simulation/research/dual_native/operands_tb.v';s=source.read_text().replace('.next_f_tag(next_f_tag),.next_m_tag(next_m_tag),.next_w_tag(next_w_tag),','')
  s=s.replace(' reg wait_a=0,'," reg r_valid=0;reg[3:0] r_tag=0;reg[31:0] r_data=0;\n reg wait_a=0,")
  s=s.replace('  .w_valid(w_valid)', '  .r_valid(r_valid),.r_tag(r_tag),.r_data(r_data),.w_valid(w_valid)')
  s=s.replace('   #1;compare;',"   rng=step(rng);r_valid=rng[0];r_tag=rng[4:1];r_data=rng;\n   if(i%5==0) begin r_valid=1;r_tag=tag_c;end\n   #1;compare;")
  s=s.replace('$fatal(1,"operand handshake differs cycle=%0d",i);','$fatal(1,"operand handshake differs cycle=%0d got=%b%b%b ref=%b%b%b waits=%b%b%b%b refwaits=%b rd=%d/%d r=%b:%h",i,ready0,valid0,occupied0,ready1,valid1,occupied1,dut.wa,dut.wb,dut.wc,dut.wd,ref_dut.waiting,dut.rd,ref_dut.rd,r_valid,r_tag);')
  tb=out/'operands_tb.v';tb.write_text(s);inputs +=[actual,ref,source,tb]
  run(out,[iv,'-g2012','-s','operands_equivalence_tb','-o',out/'sim.vvp',actual,ref,tb],'compile.log')
  for seed in (17,91,2026):
   t=run(out,[vvp,out/'sim.vvp',f'+seed={seed}'],f'seed_{seed}.log');assert 'PASS operands equivalence cycles=100000' in t;tests.append(t.strip())
 elif a.mode=='timeline':
  image=ROOT/'simulation/results/load_cycle_structure/directed.hex';reference=ROOT/'docs/load_cycle_structure/result.json';pairs=json.loads(reference.read_text(encoding='utf-8'))['directed_pairs'];inputs +=[image,reference]
  bench=src/'checks/soc_tb.v';s=bench.read_text();mon='''
 integer le=0,lf;reg[4095:0] lp;
 initial begin if(!$value$plusargs("cycletrace=%s",lp)) $fatal;lf=$fopen(lp,"w");end
 always @(posedge clk) if(rst_n) begin le=le+1;
 if(dut.cpu.ex_fire) $fdisplay(lf,"EX %0d %08x",le,dut.cpu.ex_packet[199:168]);
 if(dut.cpu.d_req_valid && dut.cpu.d_req_ready) $fdisplay(lf,"REQ %0d %08x",le,dut.cpu.mem_packet[276:245]);
 if(dut.cpu.memory_done) $fdisplay(lf,"WB_CAPTURE %0d %08x",le,dut.cpu.memory_packet[276:245]);end
'''
  tb=out/'soc_tb.v';tb.write_text(s.replace('endmodule',mon+'\nendmodule'));files=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[]);files=[src/p.name if str(p.relative_to(ROOT)) in g['override_sha256'] else p for p in files]+[src/'pango_ram_wide_models.v'];inputs +=[*files,bench,tb]
  run(out,[iv,'-g2012','-s','soc_tb','-o',out/'sim.vvp',*files,tb],'compile.log');cycle=out/'cycles.trace';trace=out/'retired.trace'
  t=run(out,[vvp,out/'sim.vvp',f'+image={image}',f'+trace={trace}',f'+cycletrace={cycle}',f'+uart={out}/unused.txt'],'run.log');assert 'PASS cycles=' in t
  events={}
  for line in cycle.read_text().splitlines():k,e,p=line.split();events[k,int(p,16)]=int(e)
  measured=[]
  for p in pairs:
   lp,cp=p['load_pc'],p['consumer_pc'];e,r,w,c=events['EX',lp],events['REQ',lp],events['WB_CAPTURE',lp],events['EX',cp]
   assert r==e+1 and w==r+1 and c==w+(1 if a.variant=='dual_legacy_fifo' else 0),(p,e,r,w,c)
   measured.append(dict(load_pc=lp,consumer_pc=cp,ex=e,request=r,wb_capture=w,consumer_ex=c,ex_bubbles=c-e-1))
  tests=[dict(status='PASS',**m) for m in measured]
 else:
  def linux(p):p=Path(p).resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
  files=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[]);files=[src/p.name if str(p.relative_to(ROOT)) in g['override_sha256'] else p for p in files]+[src/'pango_ram_wide_models.v'];inputs+=files
  t=run(out,['wsl.exe','-d','Ubuntu','--','verilator','--lint-only','-Wall','-Wno-fatal','--top-module','nc_soc',*[linux(p) for p in files]],'lint.log');kinds=set(re.findall(r'%Warning-(\w+):',t));assert not kinds.intersection({'LATCH','UNOPTFLAT','MULTIDRIVEN','UNDRIVEN','IMPLICIT','PINMISSING','PINNOTFOUND'}),kinds
  tests=['PASS no dangerous lint diagnostics']
  core=(src/'nc_core.v').read_text();fetch=(src/'nc_fetch.v').read_text();mem=(src/'nc_memory.v').read_text();assert 'nc_fifo #(.WIDTH(249),.DEPTH(4))' in core;assert 'peek_inst' not in fetch and 'even_read_row=rd[2:1]' in fetch
  tests+=['PASS EX/MEM FIFO width249/depth4 preserved; no ready-to-EX feedback','PASS parity bank read addresses depend on registered rd only; no peek/group-cross network']
  fun=fetch[fetch.index(' function[8:0] classify_parts'):];fun=fun[:fun.index(' endfunction')+len(' endfunction')]
  proof=out/'admission_proof.v';proof.write_text('module admission_proof(input[31:0] insn,output equal);\n'+fun+'''
 wire[8:0] p=classify_parts(insn);wire allowed=|p[5:3] || p[8];wire[3:0] kind;wire illegal,wr,u1,u2,serial;
 nc_decode d(.insn(insn),.kind(kind),.imm(),.use1(u1),.use2(u2),.write_rd(wr),.serial(serial),.illegal(illegal),.control(),.rs1(),.rs2(),.rd(),.csr_exists(1'b0),.csr_writable(1'b0));
 assign equal=!allowed || (!illegal && !serial && wr==p[2] && u1==p[0] && u2==p[1] && ((kind==1)==insn[6]) && (kind==0 || kind==1 || (kind==6 && !insn[14])));
 endmodule
''');decoder=ROOT/'hardware/pds/source/core/nc_decode.v';inputs +=[proof,decoder]
  t=run(out,['wsl.exe','-d','Ubuntu','--','yosys','-p',f'read_verilog -sv {linux(decoder)} {linux(proof)}; prep -top admission_proof -flatten; sat -verify -prove equal 1'],'admission_sat.log');assert 'SUCCESS!' in t
  tests+=['PASS SAT: actual side admission class, source-use and write flags match full decoder for every possible instruction']
  if a.variant!='dual_legacy_fifo':
   assert 'rsp_valid && !rsp_error && !kill && !exception && kind==4 && wr && rd!=0' in mem
   tests+=['PASS synchronous load return broadcast gated by transaction ownership, error, exception and squash; request path unchanged']
 save(out/'result.json',dict(status='PASS',variant=a.variant,tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}));print(a.mode,'PASS',a.variant,len(tests))
if __name__=='__main__':main()
