"""Reject stale checkpoints; restore canonical mapping only for identical verified inputs."""
from pathlib import Path
import argparse,json,hashlib,shutil,gzip
from compare_clock82_netlists import compare
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--project',type=Path,required=True);parser.add_argument('--install',action='store_true');args=parser.parse_args();project=args.project.resolve()
 checkpoint=project/'checkpoints';record=json.loads((checkpoint/'clock82_checkpoint.json').read_text())
 if record.get('status')=='REVOKED_WRONG_BOARD_PIN_CONSTRAINTS':raise SystemExit('Revoked board checkpoint: use tools/build_board5000.py with the ordinary PDS project')
 for n,h in record['source_input_sha256'].items():
  if sha(project/n)!=h:raise SystemExit(f'Checkpoint invalid: input changed: {n}. Run rebuild_from_rtl.tcl and repeat seed convergence; never reuse this checkpoint for changed RTL/IP/images/constraints.')
 for n,h in record['checkpoint_sha256'].items():assert sha(checkpoint/n)==h,n
 proof=compare(checkpoint/'clock82_syn.vm',project/'synthesize/top_syn.vm');assert proof['status']=='PASS'
 if args.install:
  fresh=(project/'synthesize/top_syn.vm').read_bytes();(checkpoint/'last_fresh_netlist.vm.gz').write_bytes(gzip.compress(fresh,mtime=0))
  receipt=dict(status='PASS',fresh_netlist_sha256=hashlib.sha256(fresh).hexdigest(),checkpoint_manifest_sha256=sha(checkpoint/'clock82_checkpoint.json'),source_input_sha256=record['source_input_sha256'],equivalence=proof,guard_sha256=sha(Path(__file__).resolve()))
  (checkpoint/'last_verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
  for src,dst in (('clock82_map.adf','device_map/top_map.adf'),('clock82_syn.vm','synthesize/top_syn.vm'),('clock82_mapping.dmr','device_map/top.dmr')):shutil.copyfile(checkpoint/src,project/dst)
 print('PASS: all source/IP/image/constraint hashes and complete structural connectivity match; canonical82 mapping verified'+(' and installed' if args.install else ''))
if __name__=='__main__':main()
