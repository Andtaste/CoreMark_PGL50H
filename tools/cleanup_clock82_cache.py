"""Remove only this campaign's regenerable cache after verifying frozen evidence."""
from pathlib import Path
import hashlib,json,shutil,zipfile
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'docs/clock82_multiseed_20261022'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
manifest=read(out/'manifest.json')
for n,h in manifest.items():assert sha(out/n)==h,n
assert read(out/'result.json')['status']=='CLOCK82_VERIFIED_AND_PROMOTED'
plans=[read(out/'extension_plan.json'),read(out/'route_plan.json'),*read(out/'additional_place_plans.json'),*read(out/'additional_route_plans.json'),read(out/'reproduction_plan.json')]
folders={ROOT/'hardware/pds82_seed_sweep'}
folders.update(ROOT/p['trial_directory'] for p in plans)
protected={(ROOT/p[k]).resolve() for p in plans for k in ('mapped_input_db','placement_db') if k in p}
s=read(out/'seed_results.json');r=read(out/'route_results.json')
records={**{k:x for k,x in s['seeds'].items()},**{f"p{x['gplace_seed']}_r{x['groute_seed']}":x for x in r['routes'].values()}}
for key,x in records.items():
 folder=ROOT/x['directory'];archive=out/'seeds'/key/'routed_snapshot.zip'
 with zipfile.ZipFile(archive) as z:
  assert hashlib.sha256(z.read('top_pnr.adf')).hexdigest()==x['routed_sha256']
  if x['status']=='PASS':protected.add((folder/'top_pnr.adf').resolve());protected.add((folder/'top_plc.adf').resolve())
removed=[];bytes_removed=0
for folder in sorted(folders):
 folder=folder.resolve();assert folder.is_relative_to((ROOT/'hardware').resolve()) and folder.name.startswith('pds82_'),folder
 for p in sorted(folder.rglob('*')):
  if not p.is_file():continue
  p=p.resolve();assert p.is_relative_to(folder),p
  if p in protected:continue
  rel=p.relative_to(folder)
  # Keep original map input, all source/IP/images and readable reports. Only
  # stage databases/derived netlists and already archived routed checkpoints go.
  cache=p.suffix in ('.db','.netlist')
  cache|=p.suffix=='.adf' and rel.parts[0] in ('compile','constraint_check','place_route','report_timing')
  if not cache:continue
  length=p.stat().st_size;removed.append(dict(path=str(p.relative_to(ROOT)),bytes=length,sha256=sha(p),reason='Regenerable stage cache or native route snapshot retained in verified frozen archive'))
  p.unlink();bytes_removed+=length
obj=(ROOT/'simulation/results/clock82_checks/obj').resolve()
assert obj.is_relative_to((ROOT/'simulation/results/clock82_checks').resolve()) and obj.name=='obj'
if obj.exists():
 length=sum(p.stat().st_size for p in obj.rglob('*') if p.is_file());shutil.rmtree(obj);bytes_removed+=length;removed.append(dict(path=str(obj.relative_to(ROOT)),bytes=length,reason='Regenerable Verilator compilation cache; test sources, logs and results preserved'))
for n,h in manifest.items():assert sha(out/n)==h,n
active=read(ROOT/'docs/active_pds_baseline.json');assert sha(ROOT/'docs/accepted_dual_baseline.json')==active['accepted_descriptor_sha256']
for n,h in active['input_sha256'].items():assert sha(ROOT/n)==h,n
receipt=dict(status='PASS',removed_bytes=bytes_removed,removed_mib=bytes_removed/1048576,removed=removed,protected_input_paths=[str(p.relative_to(ROOT)) for p in sorted(protected)],frozen_files_verified=len(manifest),frozen_manifest_sha256=sha(out/'manifest.json'),active_project_untouched=True)
target=ROOT/'simulation/results/clock82_cleanup.json';assert not target.exists();target.write_text(json.dumps(receipt,indent=2)+'\n')
print('CLEANED',round(bytes_removed/1048576,1),'MiB;',len(manifest),'frozen files and active82 inputs verified; main and both baseline backups untouched')
