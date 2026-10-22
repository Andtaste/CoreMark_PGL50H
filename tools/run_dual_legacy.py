"""Standard regressions, with individual-word frontend and return observers."""
import sys,json,re
import research_dual_issue as trial
def main():
 i=sys.argv.index('--variant');variant=sys.argv[i+1];del sys.argv[i:i+2]
 assert variant.startswith('dual_legacy_');trial.OUT=trial.ROOT/('simulation/results/load_bp_'+variant)
 prepare=trial.prepare_benches
 def benches(dest):
  paths=prepare(dest)
  for p in paths:
   s=p.read_text().replace('w_side[101]','w_side[64]')
   s=s.replace('dut.cpu.ex_branch','dut.cpu.resolved_branch').replace('dut.cpu.ex_prediction','dut.cpu.resolved_prediction').replace('dut.cpu.execute_taken','dut.cpu.resolved_taken').replace('dut.cpu.execute_target','dut.cpu.resolved_target')
   s=s.replace('case(dut.cpu.w_insn[6:0])',"if(dut.cpu.commit1 && dut.cpu.w1_branch) ref_bjp=ref_bjp+1;\n    case(dut.cpu.w_insn[6:0])")
   cpu='dut.cpu' if p.name=='soc_tb.v' else 'dut'
   s=s.replace(f' || {cpu}.w_kind==1 ||',f' || ({cpu}.w_kind==1 && {cpu}.w_next!={cpu}.w_pc+4) ||')
   from profile_dual_joint import instrument
   s=instrument(s,cpu,variant)
   s=s.replace(f'{cpu}.pair_issue && {cpu}.fetch.cross_window && {cpu}.fetch.metadata[{cpu}.fetch.following][31:0]!={cpu}.id_pc+4',f'{cpu}.pair_issue && {cpu}.fetch.head_1[106:75]!={cpu}.id_pc+4')
   s=s.replace(f'{cpu}.fetch.cross_window',f'{cpu}.fetch.rd[0]').replace(f'{cpu}.fetch.pop_two_groups',f'({cpu}.fetch.consume && {cpu}.fetch.pop_two)')
   if variant!='dual_legacy_fifo':
    mon='''
 integer lr_active=0,lr_exec=0,lr_capture=0;
 always @(posedge clk) if(rst_n) begin
  if(CPU.r_valid) begin
   lr_active=lr_active+1;
   if(!CPU.memory.memory_pending || !CPU.d_rsp_valid || CPU.d_error || CPU.do_trap || CPU.memory.kind!=4) $fatal(1,"Invalid load return broadcast");
   if(CPU.ex_fire) lr_exec=lr_exec+1;
   if(CPU.issue) lr_capture=lr_capture+1;
  end
 end
 always @(negedge clk) if(finish_count==1) $display("RETURN_COVER broadcasts=%0d concurrent_ex=%0d concurrent_issue=%0d",lr_active,lr_exec,lr_capture);
'''
    s=s.replace('endmodule',mon.replace('CPU',cpu)+'\nendmodule')
   p.write_text(s)
  return paths
 trial.prepare_benches=benches;original=trial.subprocess.run;model=trial.ROOT/'simulation/models/pango_ram_models.v';replacement=trial.OUT/'pango_ram_wide_models.v'
 def run(cmd,*args,**kwargs):
  cmd=[str(replacement) if str(p)==str(model) else trial.linux(replacement) if str(p)==trial.linux(model) else p for p in cmd]
  return original(cmd,*args,**kwargs)
 trial.subprocess.run=run;trial.main();phase=sys.argv[sys.argv.index('--phase')+1]
 paths=[trial.OUT/phase/'result.json']+([trial.OUT/'result.json'] if phase=='performance' else [])
 for path in paths:
  x=json.loads(path.read_text());x['variant']=variant;x['scope']='Integrated individual-word FIFO, branch/MUL, source bypass and selective slow-dependency admission; isolated, not adopted'
  for n in ('tools/run_dual_legacy.py','tools/generate_dual_legacy.py','tools/profile_dual_joint.py'):x['input_sha256'][n]=trial.sha(trial.ROOT/n)
  for key in ('input_sha256','actual_compile_sha256'):
   x[key].pop(str(model.relative_to(trial.ROOT)),None);x[key][str(replacement.relative_to(trial.ROOT))]=trial.sha(replacement)
  if phase in ('performance','validation'):
   log=(trial.OUT/phase/'simulation.log').read_text(errors='replace');m=re.search(r'JOINT_WINDOW ([^\r\n]+)',log);assert m
   x['joint']={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])}
  x['ip_sha256']=json.loads((trial.OUT/'generation.json').read_text())['ip_sha256'];trial.save(path,x)
if __name__=='__main__':main()
