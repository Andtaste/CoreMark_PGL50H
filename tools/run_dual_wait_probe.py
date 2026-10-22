"""Repeat immutable joint RTL with bench-only producer-wait classification."""
import sys,json,re,shutil
import research_dual_issue as trial
def main():
 src=trial.ROOT/'simulation/results/load_bp_dual_joint_fix';dest=trial.ROOT/'simulation/results/load_bp_dual_wait_probe';dest.mkdir(exist_ok=True)
 g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/trial.Path(n).name;assert trial.sha(p)==h;shutil.copyfile(p,dest/p.name)
 shutil.copytree(src/'ipcore',dest/'ipcore',dirs_exist_ok=True);shutil.copyfile(src/'pango_ram_wide_models.v',dest/'pango_ram_wide_models.v');shutil.copyfile(src/'generation.json',dest/'generation.json')
 trial.OUT=dest;prepare=trial.prepare_benches
 def benches(folder):
  paths=prepare(folder)
  from profile_dual_joint import instrument
  from profile_dual_wait_kinds import instrument as waits
  for p in paths:
   s=p.read_text().replace('w_side[101]','w_side[64]');cpu='dut.cpu' if p.name=='soc_tb.v' else 'dut'
   s=s.replace('dut.cpu.ex_branch','dut.cpu.resolved_branch').replace('dut.cpu.ex_prediction','dut.cpu.resolved_prediction').replace('dut.cpu.execute_taken','dut.cpu.resolved_taken').replace('dut.cpu.execute_target','dut.cpu.resolved_target')
   s=s.replace('case(dut.cpu.w_insn[6:0])',"if(dut.cpu.commit1 && dut.cpu.w1_branch) ref_bjp=ref_bjp+1;\n    case(dut.cpu.w_insn[6:0])")
   s=s.replace(f' || {cpu}.w_kind==1 ||',f' || ({cpu}.w_kind==1 && {cpu}.w_next!={cpu}.w_pc+4) ||')
   p.write_text(waits(instrument(s,cpu,'dual_joint_fix'),cpu))
  return paths
 trial.prepare_benches=benches;original=trial.subprocess.run;model=trial.ROOT/'simulation/models/pango_ram_models.v';replacement=dest/'pango_ram_wide_models.v'
 def run(cmd,*args,**kwargs):return original([str(replacement) if str(p)==str(model) else trial.linux(replacement) if str(p)==trial.linux(model) else p for p in cmd],*args,**kwargs)
 trial.subprocess.run=run;trial.main();phase=sys.argv[sys.argv.index('--phase')+1]
 for p in [dest/phase/'result.json']+([dest/'result.json'] if phase=='performance' else []):
  x=json.loads(p.read_text());ref=json.loads((src/phase/'result.json').read_text());log=(dest/phase/'simulation.log').read_text(errors='replace')
  for k in ['metrics','dual','multiply','predictor']:assert x[k]==ref[k],k
  m=re.search(r'WAIT_KIND ([^\r\n]+)',log);assert m;x['wait_kinds']={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])}
  assert x['wait_kinds']['all']==int(x['metrics']['EX operand wait'].split()[0])
  x['variant']='dual_wait_probe';x['parent_profile_identical']=True
  for n in ['tools/run_dual_wait_probe.py','tools/profile_dual_wait_kinds.py','tools/profile_dual_joint.py']:x['input_sha256'][n]=trial.sha(trial.ROOT/n)
  for key in ['input_sha256','actual_compile_sha256']:
   x[key].pop(str(model.relative_to(trial.ROOT)),None);x[key][str(replacement.relative_to(trial.ROOT))]=trial.sha(replacement)
  trial.save(p,x)
 print(json.dumps(x['wait_kinds'],indent=2))
if __name__=='__main__':main()
