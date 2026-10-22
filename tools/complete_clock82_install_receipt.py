"""Recover only an interrupted post-copy receipt write; re-verify every installed input."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'docs/clock82_multiseed_20261022'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
main=ROOT/'hardware/pds';trial=ROOT/'hardware/pds82_seed_sweep';backup=ROOT/'hardware/pds80_before_clock82_20261022'
assert not (out/'promotion.json').exists()
prep=read(out/'prepared.json');selection=out/'candidate_p22_r4.json';chosen=read(selection)['chosen'];assert chosen['status']=='PASS'
for n,h in read(out/'before80_full_backup_manifest.json').items():assert sha(backup/n)==h,n
for n,h in prep['before80_source_sha256'].items():
 if n.replace('\\','/').startswith(('source/','ipcore/','constraints/','memory/')):assert sha(backup/n)==h,n
before=(trial/'memory/boot_interleaved.hex').as_posix().encode();after=(main/'memory/boot_interleaved.hex').as_posix().encode()
installed={}
for folder in ('source','ipcore','constraints','memory'):
 for p in (trial/folder).rglob('*'):
  if not p.is_file() or p.suffix not in ('.v','.idf','.fdc','.hex'):continue
  target=main/p.relative_to(trial);expected=p.read_bytes()
  if folder=='ipcore':expected=expected.replace(before,after)
  assert target.read_bytes()==expected,target
  installed[str(target.relative_to(ROOT))]=sha(target)
assert 'pnr -gplace_seed 22 -gplace_times 1' in (main/'new_core.tcl').read_text() and '-groute_seed 4' in (main/'new_core.tcl').read_text()
assert sha(ROOT/'docs/accepted_dual_baseline.json')==prep['accepted_descriptor_sha256']
record=dict(status='MAIN_INPUTS_UPDATED_REBUILD_PENDING',chosen_seed=22,chosen_route_seed=4,selection_file=str(selection.relative_to(ROOT)),selection_sha256=sha(selection),requested_clock_hz=82000000,previous_main_project=str(backup.relative_to(ROOT)),input_sha256=installed,tcl_sha256=sha(main/'new_core.tcl'),cpu_logic_changed=False,receipt_recovery='Install completed; receipt writing initially failed because candidate path was relative. All backup and installed inputs independently verified before this receipt. Acceptance binding remains80MHz until native main rebuild passes.')
(out/'promotion.json').write_text(json.dumps(record,indent=2)+'\n');print('INSTALLED82 inputs verified; backup verified; receipt recovered; native main rebuild required')
