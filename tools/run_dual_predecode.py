"""Use the same test harness for registered frontend pairing hints."""
import research_dual_issue as trial
import sys,json
if __name__=='__main__':
 trial.OUT=trial.ROOT/'simulation/results/load_bp_dual_issue_predecode'
 if '--extra' in sys.argv:
  import check_dual_issue as checks
  checks.OUT=trial.OUT;checks.main();paths=[trial.OUT/'dual_checks/result.json']
 else:
  trial.main();phase=sys.argv[sys.argv.index('--phase')+1]
  paths=[trial.OUT/phase/'result.json']+([trial.OUT/'result.json'] if phase=='performance' else [])
 for path in paths:
  x=json.loads(path.read_text());x['variant']='dual_issue_predecode'
  for n in ('tools/run_dual_predecode.py','tools/generate_dual_predecode.py'):x['input_sha256'][n]=trial.sha(trial.ROOT/n)
  trial.save(path,x)
