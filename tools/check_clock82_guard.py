"""Exercise checkpoint CLI rejection using an isolated temporary project."""
from pathlib import Path
import json,hashlib,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];main=ROOT/'hardware/pds';out=ROOT/'simulation/results/clock82_guard_checks';out.mkdir(exist_ok=True)
fixture=(out/'fixture').resolve();assert not fixture.exists();fixture.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record=json.loads((main/'checkpoints/clock82_checkpoint.json').read_text())
for n in record['source_input_sha256']:
 p=(fixture/n).resolve();assert p.is_relative_to(fixture);p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(main/n,p)
shutil.copytree(main/'checkpoints',fixture/'checkpoints');(fixture/'synthesize').mkdir();(fixture/'device_map').mkdir()
shutil.copyfile(main/'checkpoints/clock82_syn.vm',fixture/'synthesize/top_syn.vm')
guard=ROOT/'tools/verify_clock82_checkpoint.py'
def run():return subprocess.run([sys.executable,'-X','utf8',str(guard),'--project',str(fixture),'--install'],capture_output=True,text=True)
first=run();assert first.returncode==0,first.stderr
mapped=sha(fixture/'device_map/top_map.adf');receipt=sha(fixture/'checkpoints/last_verification.json')
p=fixture/'source/core/nc_core.v';original=p.read_bytes();p.write_bytes(original+b'\n// isolated stale-input guard test\n')
second=run();assert second.returncode!=0 and 'Checkpoint invalid: input changed' in second.stderr
assert sha(fixture/'device_map/top_map.adf')==mapped and sha(fixture/'checkpoints/last_verification.json')==receipt
p.write_bytes(original)
p=fixture/'synthesize/top_syn.vm';v=p.read_text();assert '.RADDR (' in v;p.write_text(v.replace('.RADDR (','.RADDR (32\'h12345678 ^ ',1))
third=run();assert third.returncode!=0 and 'AssertionError' in third.stderr
assert sha(fixture/'device_map/top_map.adf')==mapped and sha(fixture/'checkpoints/last_verification.json')==receipt
x=dict(status='PASS',tests=['Exact inputs/connectivity accepted and installed','Changed RTL rejected before checkpoint installation','Changed synthesized RAM connection rejected before checkpoint installation'],all_negative_cases_preserve_installed_map_and_prior_receipt=True,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in (guard,ROOT/'tools/compare_clock82_netlists.py',Path(__file__).resolve(),main/'checkpoints/clock82_checkpoint.json')},positive_stdout=first.stdout,stale_source_error=second.stderr,structural_mismatch_error=third.stderr)
(out/'result.json').write_text(json.dumps(x,indent=2)+'\n')
assert fixture.is_relative_to(out.resolve()) and fixture.name=='fixture';shutil.rmtree(fixture)
print('PASS exact-input guard; stale RTL and changed compiled connection both rejected without installing an old map')
