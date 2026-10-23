"""Remove late pair admission from side operand data capture, retaining wait ownership."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'simulation/results/autonomous_20261022'

def main():
 manifest=ROOT/'docs/active_optimization_baseline.json'
 m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 assert m['source_trial']=='mul_early_products'
 for name,digest in m['input_sha256'].items():
  assert hashlib.sha256((src/name).read_bytes()).hexdigest()==digest,name
 dest=WORK/'side_capture_dep';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):
  shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(manifest,dest/'parent_baseline.json')
 p=dest/'source/core/nc_core.v';s=p.read_text()
 old='  .wait_c(pair_candidate && dep_c),.wait_d(pair_candidate && dep_d),.tag_c(tag_c),.tag_d(tag_d),';assert s.count(old)==1
 s=s.replace(old,'  .capture_dep_c(dep_c),.capture_dep_d(dep_d),\n'+old);p.write_text(s)
 p=dest/'source/core/nc_operands.v';s=p.read_text()
 old=' input wire wait_c,wait_d,input wire[3:0] tag_c,tag_d,';assert s.count(old)==1
 s=s.replace(old,' input wire capture_dep_c,capture_dep_d,\n'+old)
 for lane in ('c','d'):
  pattern=r' wire\[31:0\] incoming_'+lane+r'=[^\n]+'
  match=re.search(pattern,s);assert match
  line=match[0];assert line.count('wait_'+lane)==5
  s=s.replace(line,line.replace('wait_'+lane,'capture_dep_'+lane))
 p.write_text(s)
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=m['source_trial'],intent='Use raw side dependencies for speculative free-slot data sampling; retain pair-qualified wait/valid state. Inactive side data is unobserved. Targets measured pair_candidate to incoming_c path.'),indent=2)+'\n')
 print('PREPARED',dest.name)

if __name__=='__main__':main()
