"""Allow a multiply's side lane to share dependencies already required by lane zero."""
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
 dest=WORK/'mul_shared_dep_pair';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):
  shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(manifest,dest/'parent_baseline.json')
 p=dest/'source/core/nc_core.v';s=p.read_text()
 old=' wire pair_candidate=!(id_mul_hint && (dep_c || dep_d)) && id_second';assert s.count(old)==1
 new=''' // A side operand waiting for the same token as a primary operand
 // cannot impose an additional producer dependency on the multiply group.
 wire independent_wait_c=dep_c && !((dep_a && tag_c==tag_a) || (dep_b && tag_c==tag_b));
 wire independent_wait_d=dep_d && !((dep_a && tag_d==tag_a) || (dep_b && tag_d==tag_b));
 wire pair_candidate=!(id_mul_hint && (independent_wait_c || independent_wait_d)) && id_second'''
 p.write_text(s.replace(old,new))
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=m['source_trial'],intent='Pair main multiply with side operands only when all live side dependencies are also primary dependencies; preserve intra-pair RAW/WAW exclusions'),indent=2)+'\n')
 print('PREPARED',dest.name)

if __name__=='__main__':main()
