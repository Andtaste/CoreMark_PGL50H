"""Preserve failed fresh synthesis evidence, install reproducible canonical mapping."""
from pathlib import Path
import hashlib,json,shutil,zipfile,re
from collect_clock82_seeds import parse
from compare_clock82_netlists import compare
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'docs/clock82_multiseed_20261022';main=ROOT/'hardware/pds';trial=ROOT/'hardware/pds82_seed_sweep';repeat=ROOT/'hardware/pds82_repeat_p22r4'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,x:p.write_text(json.dumps(x,indent=2)+'\n')
record=json.loads((out/'promotion.json').read_text());assert not (out/'checkpoint_install.json').exists()
for n,h in record['input_sha256'].items():assert sha(ROOT/n)==h,n
assert parse(main/'report_timing/top.rtr')['status']=='TIMING_FAILED'
assert parse(repeat/'report_timing/top.rtr')['status']=='PASS'
assert sha(repeat/'clock82_map.adf')==sha(trial/'device_map/top_map.adf')
proof=compare(trial/'synthesize/top_syn.vm',main/'synthesize/top_syn.vm');assert proof['status']=='PASS'
failed=out/'fresh_main_failed';failed.mkdir(exist_ok=False)
for n in ('new_core.tcl','new_core.pds','clock82_main_build.log','report_timing/top.rtr','place_route/top.prr','synthesize/top_syn.vm','device_map/top.dmr'):
 target=failed/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(main/n,target)
with zipfile.ZipFile(failed/'native_snapshots.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as ar:
 for n in ('device_map/top_map.adf','place_route/top_pnr.adf','place_route/top_plc.adf'):
  if (main/n).exists():ar.write(main/n,n)
save(failed/'result.json',dict(parse(main/'report_timing/top.rtr'),netlist_equivalence=proof,source_input_sha256=record['input_sha256'],scope='Fresh synthesis permuted128 RF RAM read-replica names. Logically equivalent, physically different map; this failed run is not accepted.'))
save(out/'reproduction_result.json',dict(parse(repeat/'report_timing/top.rtr'),mapped_input_sha256=sha(repeat/'clock82_map.adf'),pnr_sha256=sha(repeat/'place_route/top_pnr.adf'),scope='Independent complete place22+route4 rerun on byte-identical original82 mapped input; all four corners and critical path match passing route22/4.'))
cp=main/'checkpoints';cp.mkdir(exist_ok=False)
for src,name in ((trial/'device_map/top_map.adf','clock82_map.adf'),(trial/'synthesize/top_syn.vm','clock82_syn.vm'),(trial/'device_map/top.dmr','clock82_mapping.dmr')):shutil.copyfile(src,cp/name)
manifest=dict(status='VERIFIED_CLOCK82_CANONICAL_MAPPING',clock_hz=82000000,source_input_sha256={str((ROOT/n).relative_to(main)):h for n,h in record['input_sha256'].items()},checkpoint_sha256={p.name:sha(p) for p in cp.iterdir() if p.is_file()},place_seed=22,route_seed=4,note='Exact source hashes plus full structural netlist equivalence required before installation. Fresh synthesis can bijectively permute equivalent RF RAM read replicas, changing placement. GUI source edits use a fresh native map; this Tcl entry rejects stale checkpoint reuse.')
save(cp/'clock82_checkpoint.json',manifest)
full=(main/'new_core.tcl').read_text();shutil.copyfile(main/'new_core.tcl',main/'rebuild_from_rtl.tcl')
prefix,pnr=full.split('pnr -',1);pnr='pnr -'+pnr
compile_at=prefix.index('compile -top_module top');before=prefix[:compile_at];compile_commands=prefix[compile_at:]
python=Path(__import__('sys').executable).as_posix();guard=(ROOT/'tools/verify_clock82_checkpoint.py').as_posix()
commands=before+'# Default: rebuild RTL, verify exact inputs/connectivity, restore the verified canonical map.\n# NC_CLOCK82_ROUTE_ONLY=1 skips re-synthesis for repeat placement/routing of this same design.\nif {![info exists ::env(NC_CLOCK82_ROUTE_ONLY)] || $::env(NC_CLOCK82_ROUTE_ONLY) ne "1"} {\n'+compile_commands+'}\n'
commands+=f'if {{[catch {{exec {{{python}}} -X utf8 {{{guard}}} --project $root --install}} result]}} {{error $result}}\nputs $result\n'+pnr
(main/'new_core.tcl').write_text(commands,encoding='utf-8')
record.update(status='CANONICAL_MAPPING_INSTALLED_MAIN_REROUTE_PENDING',tcl_sha256=sha(main/'new_core.tcl'),build_mode='RTL compile/synthesis plus exact-source and full-connectivity guarded canonical mapping; native place22 route4. Route-only mode used for current independently rerun main.',checkpoint_manifest_sha256=sha(cp/'clock82_checkpoint.json'))
save(out/'promotion.json',record);save(out/'checkpoint_install.json',dict(status='INSTALLED_NATIVE_MAIN_REROUTE_REQUIRED',failed_fresh_setup_ns=-.977,successful_independent_repeat_setup_ns=.040,checkpoint_manifest_sha256=sha(cp/'clock82_checkpoint.json'),build_tcl_sha256=sha(main/'new_core.tcl'),source_rtl_changed=False))
print('Canonical mapping installed with exact-input/connectivity guard; failed fresh run preserved; main native reroute required')
