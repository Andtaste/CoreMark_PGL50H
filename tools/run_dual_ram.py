"""Reuse the same dual-issue harness and fixed images for RAM organization trials."""
from pathlib import Path
import sys,json
import research_dual_issue as trial
def main():
 wide='--wide' in sys.argv
 if wide:sys.argv.remove('--wide')
 variant='dual_ram'+('_wide' if wide else '');trial.OUT=trial.ROOT/('simulation/results/load_bp_'+variant)
 prepare=trial.prepare_benches
 def benches(dest):
  paths=prepare(dest)
  for p in paths:p.write_text(p.read_text().replace('w_side[101]','w_side[64]'))
  return paths
 trial.prepare_benches=benches
 # Only replace the functional model passed to the compiler, retaining an
 # explicit hash of the actual model. No production file is substituted on disk.
 original=trial.subprocess.run
 model=trial.ROOT/'simulation/models/pango_ram_models.v';replacement=trial.OUT/'pango_ram_wide_models.v'
 def run(cmd,*args,**kwargs):
  if wide:cmd=[str(replacement) if str(p)==str(model) else trial.linux(replacement) if str(p)==trial.linux(model) else p for p in cmd]
  return original(cmd,*args,**kwargs)
 trial.subprocess.run=run
 trial.main();phase=sys.argv[sys.argv.index('--phase')+1]
 for path in [trial.OUT/phase/'result.json']+([trial.OUT/'result.json'] if phase=='performance' else []):
  x=json.loads(path.read_text());x['variant']=variant
  for n in ('tools/run_dual_ram.py','tools/generate_dual_ram.py'):x['input_sha256'][n]=trial.sha(trial.ROOT/n)
  if wide:
   for key in ('input_sha256','actual_compile_sha256'):
    x[key].pop(str(model.relative_to(trial.ROOT)),None)
    x[key][str(replacement.relative_to(trial.ROOT))]=trial.sha(replacement)
   x['ip_sha256']=json.loads((trial.OUT/'generation.json').read_text())['ip_sha256']
  trial.save(path,x)
if __name__=='__main__':main()
