"""Install a fully passing 82MHz seed's inputs; rebuild main PDS independently."""
from pathlib import Path
import hashlib,json,re,shutil,argparse
from collect_clock82_seeds import parse
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 out=ROOT/'docs/clock82_multiseed_20261022';seeds=json.loads((out/'seed_results.json').read_text());checks=json.loads((ROOT/'simulation/results/clock82_checks/result.json').read_text());prep=json.loads((out/'prepared.json').read_text(encoding='utf-8'))
 parser=argparse.ArgumentParser();parser.add_argument('--candidate',type=Path);args=parser.parse_args()
 selection_file=(args.candidate or out/'selected_config.json').resolve();selection=json.loads(selection_file.read_text())
 assert (args.candidate is not None or (seeds['status']=='COMPLETE' and selection.get('status')=='COMPLETE')) and selection['chosen'] is not None and checks['status']=='PASS';best=selection['chosen']['gplace_seed'];route_seed=selection['chosen']['groute_seed']
 assert selection['chosen']['status']=='PASS'
 chosen_directory=ROOT/selection['chosen']['directory']
 assert parse(chosen_directory/'top.rtr')['status']=='PASS'
 assert sha(chosen_directory/'top.rtr')==selection['chosen']['sta_sha256']
 assert sha(chosen_directory/'top_pnr.adf')==selection['chosen']['routed_sha256']
 main=ROOT/'hardware/pds';src=ROOT/prep['trial_directory'];assert not (out/'promotion.json').exists()
 # A source edit by someone else is never silently overwritten. GUI-generated
 # implementation records are snapshotted separately at preparation time.
 for p in (main/'source').rglob('*.v'):
  relative=str(p.relative_to(main));assert sha(p)==prep['before80_source_sha256'][relative],p
 backup=ROOT/'hardware/pds80_before_clock82_20261022';assert not backup.exists()
 shutil.copytree(main,backup)
 backup_manifest={str(p.relative_to(backup)):sha(p) for p in backup.rglob('*') if p.is_file()}
 (out/'before80_full_backup_manifest.json').write_text(json.dumps(backup_manifest,indent=2)+'\n')
 for n in ('accepted_dual_baseline.json','active_pds_baseline.json'):shutil.copyfile(ROOT/'docs'/n,out/('previous_'+n))
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,main/folder,dirs_exist_ok=True)
 before=(src/'memory/boot_interleaved.hex').as_posix().encode();after=(main/'memory/boot_interleaved.hex').as_posix().encode()
 for p in (main/'ipcore').rglob('*'):
  if p.is_file() and p.suffix in ('.v','.idf','.vhdl'):p.write_bytes(p.read_bytes().replace(before,after))
 prefix=(src/'new_core.tcl').read_text().split('pnr -',1)[0]
 pnr=f'pnr -gplace_seed {best} -gplace_times 1 -saved_outcome 1 -parallel 1 -groute_seed {route_seed} -groute_times 1 -max_ctrl_chain_length 4 -optimize_multi_corner_timing -fix_hold_violation -fix_hold_violation_in_route TRUE'
 pnr+=' '+selection['chosen'].get('pnr_options','')
 (main/'new_core.tcl').write_text('# Verified 82MHz target; chosen seed from the frozen multi-seed sweep.\n'+prefix+pnr+'\nreport_timing -max_path 30 -nworst 1\n',encoding='utf-8')
 # Native PDS will refresh these stage states after actual compile/map/route.
 p=main/'new_core.pds';p.write_text(re.sub(r'\(_gci_state \(_integer [0-9]+\)\)','(_gci_state (_integer 0))',p.read_text()),encoding='utf-8')
 record=dict(status='MAIN_INPUTS_UPDATED_REBUILD_PENDING',chosen_seed=best,chosen_route_seed=route_seed,selection_file=str(selection_file.relative_to(ROOT)),selection_sha256=sha(selection_file),requested_clock_hz=82000000,previous_main_project=str(backup.relative_to(ROOT)),input_sha256={str(p.relative_to(ROOT)):sha(p) for folder in ('source','ipcore','constraints','memory') for p in (main/folder).rglob('*') if p.is_file() and p.suffix in ('.v','.idf','.fdc','.hex')},tcl_sha256=sha(main/'new_core.tcl'),cpu_logic_changed=False,note='User requested real82MHz; acceptance binding changes only after main-directory native build passes. Existing open GUI must reload the project to see the new generated stages.')
 (out/'promotion.json').write_text(json.dumps(record,indent=2)+'\n');print('INSTALLED main82 inputs, selected seed',best,'; full rebuild required')
if __name__=='__main__':main()
