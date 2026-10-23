"""Split the measured direct-load address carry chain, preserving cycle behavior."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'simulation/results/autonomous_20261022'

def main():
 manifest=ROOT/'docs/active_optimization_baseline.json'
 m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 for name,digest in m['input_sha256'].items():
  assert hashlib.sha256((src/name).read_bytes()).hexdigest()==digest,name
 dest=WORK/'direct_agu_csel';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):
  shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(manifest,dest/'parent_baseline.json')
 p=dest/'source/core/nc_core.v';s=p.read_text()
 old=' wire[31:0] direct_agu=ex_packet[135:104]+ex_packet[71:40];'
 assert s.count(old)==1
 new=''' // Compute both high halves in parallel with the low-half carry.
 wire[31:0] agu_a=ex_packet[135:104],agu_b=ex_packet[71:40];
 wire[16:0] agu_low={1'b0,agu_a[15:0]}+{1'b0,agu_b[15:0]};
 wire[15:0] agu_high0=agu_a[31:16]+agu_b[31:16];
 wire[15:0] agu_high1=agu_a[31:16]+agu_b[31:16]+16'd1;
 wire[31:0] direct_agu={agu_low[16] ? agu_high1 : agu_high0,agu_low[15:0]};'''
 p.write_text(s.replace(old,new))
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=m['source_trial'],intent='16+16 carry-select on direct load address only; cycle equivalent; motivated by baseline worst STA path to RAM enable'),indent=2)+'\n')
 print('PREPARED',dest.name)

if __name__=='__main__':main()
