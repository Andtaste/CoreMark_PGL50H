"""Only if first ten fail narrowly, try ten more place seeds on the same map DB."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 out=ROOT/'docs/clock82_multiseed_20261022';x=json.loads((out/'seed_results.json').read_text());assert x['status']=='COMPLETE' and x['completed']==10 and not x['passing']
 best=max(v['corners']['Setup Summary(Slow Corner)']['worst_slack_ns'] for v in x['seeds'].values());assert best>=-0.1,best
 trial=ROOT/'hardware/pds82_seed_sweep';dest=ROOT/'hardware/pds82_seed_sweep_more';assert not dest.exists() and not (out/'extension_plan.json').exists();dest.mkdir()
 db=trial/'device_map/top_map.adf';assert db.is_file()
 command='pnr -input_db_file {'+db.as_posix()+'} -gplace_seed 10 -gplace_times 10 -seed_step 1 -saved_outcome 10 -parallel 3 -max_ctrl_chain_length 4 -optimize_multi_corner_timing -fix_hold_violation -fix_hold_violation_in_route TRUE'
 tcl=dest/'more_seeds.tcl';tcl.write_text('set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\n'+command+'\nreport_timing -max_path 30 -nworst 1\n')
 plan=dict(status='PREPARED',reason='No full-corner pass in seeds0..9, best setup is within0.1ns; bounded extra10 seeds, no RTL/PLL/constraint change or re-synthesis',seeds=list(range(10,20)),parallel=3,trial_directory=str(dest.relative_to(ROOT)),mapped_input_db=str(db.relative_to(ROOT)),mapped_db_sha256=sha(db),tcl_sha256=sha(tcl),pnr_command=command)
 (out/'first10_seed_results.json').write_bytes((out/'seed_results.json').read_bytes());(out/'extension_plan.json').write_text(json.dumps(plan,indent=2)+'\n');print('PREPARED extra seeds10..19, exact same 82MHz mapped DB')
if __name__=='__main__':main()
