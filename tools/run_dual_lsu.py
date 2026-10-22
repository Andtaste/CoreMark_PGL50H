"""Architectural and fixed-image checks with an independent second RAM responder."""
import sys,json,re
import research_dual_issue as trial
def main():
 i=sys.argv.index('--variant');variant=sys.argv[i+1];del sys.argv[i:i+2];assert variant in ('dual_lsu_shared','dual_lsu_ports')
 trial.OUT=trial.ROOT/('simulation/results/load_bp_'+variant);prepare=trial.prepare_benches
 def benches(dest):
  ps=prepare(dest)
  for p in ps:
   cpu='dut.cpu' if p.name=='soc_tb.v' else 'dut';s=p.read_text().replace('w_side[101]','w_side[64]')
   s=s.replace('dut.cpu.ex_branch','dut.cpu.resolved_branch').replace('dut.cpu.ex_prediction','dut.cpu.resolved_prediction').replace('dut.cpu.execute_taken','dut.cpu.resolved_taken').replace('dut.cpu.execute_target','dut.cpu.resolved_target')
   s=s.replace(f' || {cpu}.w_kind==1 ||',f' || ({cpu}.w_kind==1 && {cpu}.w_next!={cpu}.w_pc+4) ||')
   if p.name=='core_tb.v':
    s=s.replace(' nc_core dut(',''' wire sv,sr,sov,sor,swrite;wire[31:0] sa,sw,sdata;wire[3:0] sm;
 nc_core dut(.s_req_valid(sv),.s_req_ready(sr),.s_addr(sa),.s_wdata(sw),.s_mask(sm),.s_write(swrite),.s_rsp_valid(sov),.s_rsp_ready(sor),.s_rdata(sdata),''')
    block='''
 reg spending=0,srsp=0;reg[31:0] sq=0;integer sdelay=0,si;
 reg shold=0;reg[68:0] lasts;
 assign sr=!spending && !srsp && lfsr[13];assign sov=srsp;assign sdata=sq;
 always @(posedge clk) if(rst_n) begin
  if(shold && (!sv || {swrite,sm,sw,sa}!==lasts)) $fatal(1,"Side request changed under backpressure");
  shold<=sv && !sr;lasts<={swrite,sm,sw,sa};
  if(sv && sr) begin
   if(index(sa)<0) $fatal(1,"Non-local secondary request");
   if(dv && dr && da[31:3]==sa[31:3] && (dwrite || swrite)) $fatal(1,"Unsafe same-line dual memory issue");
   spending<=1;sdelay<=1+lfsr[16:14];sq<=mem[index(sa)];
   if(swrite) for(si=0;si<4;si=si+1) if(sm[si]) mem[index(sa)][8*si+:8]<=sw[8*si+:8];
  end
  if(spending) begin if(sdelay==0) begin spending<=0;srsp<=1;end else sdelay<=sdelay-1;end
  if(srsp && sor) srsp<=0;
 end
'''
    s=s.replace('endmodule',block+'\nendmodule')
   else:
    s=s.replace('case(dut.cpu.w_insn[6:0])',"if(dut.cpu.commit1) case(dut.cpu.w1_insn[6:0]) 7'h03:ref_loads=ref_loads+1;7'h23:ref_stores=ref_stores+1;7'h63:ref_bjp=ref_bjp+1;default:;endcase\n    case(dut.cpu.w_insn[6:0])")
   monitor='''
 integer ls_load=0,ls_store=0,ls_dual=0,ls_req=0,ls_replay=0,ls_pairs=0,ls_mainmem=0,ls_ifwait=0;
 always @(posedge clk) if(rst_n) begin
  if(CPU.s_req_valid && (!(CPU.s_addr<32'h10000 || (CPU.s_addr>=32'h10000000 && CPU.s_addr<32'h10008000)))) $fatal(1,"Secondary LSU left local RAM");
  if(CPU.s_req_valid && CPU.s_write && CPU.memory.primary_need && !CPU.memory.can_start && !CPU.memory.primary_safe) $fatal(1,"Side store passed unresolved primary");
  if(CPU.csr.stats.control && CPU.csr.stats.control_data[1]) begin ls_load=0;ls_store=0;ls_dual=0;ls_req=0;ls_replay=0;ls_pairs=0;ls_mainmem=0;ls_ifwait=0;end
  else if(!CPU.csr.stats.control && CPU.csr.stats.enabled) begin
   if(CPU.commit1 && CPU.w1_load) ls_load=ls_load+1;
   if(CPU.commit1 && CPU.w1_store) ls_store=ls_store+1;
   if(CPU.s_req_valid && CPU.s_req_ready) begin ls_req=ls_req+1;if(CPU.d_req_valid && CPU.d_req_ready) ls_dual=ls_dual+1;end
   if(CPU.side_replay) ls_replay=ls_replay+1;
   if(CPU.pair_issue && (CPU.id_side_kind==4 || CPU.id_side_kind==5)) begin ls_pairs=ls_pairs+1;if(CPU.id_kind==4 || CPU.id_kind==5) ls_mainmem=ls_mainmem+1;end
   if(CPU.i_req_valid && !CPU.i_req_ready) ls_ifwait=ls_ifwait+1;
  end
 end
 always @(negedge clk) if(check_secondary) $display("LSU_WINDOW side_load=%0d side_store=%0d same_cycle_dual_request=%0d secondary_requests=%0d replay=%0d memory_pairs=%0d dual_memory_pairs=%0d if_wait=%0d",ls_load,ls_store,ls_dual,ls_req,ls_replay,ls_pairs,ls_mainmem,ls_ifwait);
'''
   s=s.replace('endmodule',monitor.replace('CPU',cpu)+'\nendmodule');p.write_text(s)
  return ps
 trial.prepare_benches=benches;original=trial.subprocess.run;model=trial.ROOT/'simulation/models/pango_ram_models.v';replacement=trial.OUT/'pango_ram_wide_models.v'
 def run(cmd,*args,**kwargs):return original([str(replacement) if str(p)==str(model) else trial.linux(replacement) if str(p)==trial.linux(model) else p for p in cmd],*args,**kwargs)
 trial.subprocess.run=run;trial.main();phase=sys.argv[sys.argv.index('--phase')+1]
 for p in [trial.OUT/phase/'result.json']+([trial.OUT/'result.json'] if phase=='performance' else []):
  x=json.loads(p.read_text());x['variant']=variant;x['scope']='Secondary local RAM LSU, sliding word FIFO and expanded pairing; accepted baseline unchanged; no early memory request or raw return bypass; not adopted'
  for n in ('tools/run_dual_lsu.py','tools/generate_dual_lsu.py'):x['input_sha256'][n]=trial.sha(trial.ROOT/n)
  for key in ('input_sha256','actual_compile_sha256'):
   x[key].pop(str(model.relative_to(trial.ROOT)),None);x[key][str(replacement.relative_to(trial.ROOT))]=trial.sha(replacement)
  if phase in ('performance','validation'):
   text=(trial.OUT/phase/'simulation.log').read_text(errors='replace');m=re.search(r'LSU_WINDOW ([^\r\n]+)',text);assert m;x['lsu']={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])}
  x['ip_sha256']=json.loads((trial.OUT/'generation.json').read_text())['ip_sha256'];trial.save(p,x)
if __name__=='__main__':main()
