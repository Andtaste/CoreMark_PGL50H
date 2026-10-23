"""Screen a smaller spill FIFO while preserving its registered credit boundary."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'simulation/results/autonomous_20261022'
def main():
 manifest=ROOT/'docs/active_optimization_baseline.json';m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 for n,h in m['input_sha256'].items():assert hashlib.sha256((src/n).read_bytes()).hexdigest()==h,n
 dest=WORK/'memq2';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(manifest,dest/'parent_baseline.json')
 p=dest/'source/core/nc_core.v';s=p.read_text();old='nc_fifo #(.WIDTH(249),.DEPTH(4)) memory_queue';assert s.count(old)==1
 p.write_text(s.replace(old,'nc_fifo #(.WIDTH(249),.DEPTH(2)) memory_queue'))
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=m['source_trial'],intent='Reduce spill FIFO depth4 to depth2; direct handoff and registered credit unchanged'),indent=2)+'\n')
 print('PREPARED memq2')
if __name__=='__main__':main()
