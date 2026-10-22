"""Unchanged dual-core harness with candidate operand forwarding and original wide IP model."""
import sys,json
import research_dual_issue as trial
def main():
 i=sys.argv.index('--variant');variant=sys.argv[i+1];del sys.argv[i:i+2]
 assert variant in ('dual_window_cross','dual_window_both')
 trial.OUT=trial.ROOT/('simulation/results/load_bp_'+variant)
 if '--extra' in sys.argv:
  import check_dual_admit_extra as extra
  extra.OUT=trial.OUT;extra.main();paths=[trial.OUT/'dual_checks/result.json']
 else:
  prepare=trial.prepare_benches
  def benches(dest):
   paths=prepare(dest)
   for p in paths:p.write_text(p.read_text().replace('w_side[101]','w_side[64]'))
   from profile_dual_admit import instrument
   for p in paths:p.write_text(instrument(p.read_text(), 'dut.cpu' if p.name=='soc_tb.v' else 'dut', variant in ('dual_window_cross','dual_window_both')))
   return paths
  trial.prepare_benches=benches;original=trial.subprocess.run;model=trial.ROOT/'simulation/models/pango_ram_models.v';replacement=trial.OUT/'pango_ram_wide_models.v'
  def run(cmd,*args,**kwargs):
   cmd=[str(replacement) if str(p)==str(model) else trial.linux(replacement) if str(p)==trial.linux(model) else p for p in cmd]
   return original(cmd,*args,**kwargs)
  trial.subprocess.run=run
  reuse='--reuse-phase' in sys.argv
  if reuse:sys.argv.remove('--reuse-phase')
  if not reuse:trial.main()
  phase=sys.argv[sys.argv.index('--phase')+1]
  paths=[trial.OUT/phase/'result.json']+([trial.OUT/'result.json'] if phase=='performance' else [])
 for path in paths:
  x=json.loads(path.read_text());x['variant']=variant
  for n in ('tools/run_dual_window.py','tools/generate_dual_window.py'):x['input_sha256'][n]=trial.sha(trial.ROOT/n)
  if '--extra' not in sys.argv:
   for key in ('input_sha256','actual_compile_sha256'):
    x[key].pop(str(model.relative_to(trial.ROOT)),None);x[key][str(replacement.relative_to(trial.ROOT))]=trial.sha(replacement)
  if '--extra' not in sys.argv and phase in ('performance','validation'):
   import re
   log=(trial.OUT/phase/'simulation.log').read_text(errors='replace');m=re.search(r'ADMISSION_WINDOW ([^\r\n]+)',log);assert m
   x['admission']={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])}
  if '--extra' not in sys.argv:x['completed_simulation_reused_after_parser_failure']=reuse
  x['input_sha256']['tools/profile_dual_admit.py']=trial.sha(trial.ROOT/'tools/profile_dual_admit.py')
  x['ip_sha256']=json.loads((trial.OUT/'generation.json').read_text())['ip_sha256'];trial.save(path,x)
if __name__=='__main__':main()
