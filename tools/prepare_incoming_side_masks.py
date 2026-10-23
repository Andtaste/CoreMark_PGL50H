"""Factor late side wait qualification after parallel priority selection."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'simulation/results/autonomous_20261022'

def main():
 manifest=ROOT/'docs/active_optimization_baseline.json'
 m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 for name,digest in m['input_sha256'].items():
  assert hashlib.sha256((src/name).read_bytes()).hexdigest()==digest,name
 dest=WORK/'incoming_side_masks';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):
  shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(manifest,dest/'parent_baseline.json')
 p=dest/'source/core/nc_operands.v';s=p.read_text()
 for lane,bits in [('c','135:104'),('d','103:72')]:
  old=re.search(r' wire\[31:0\] incoming_'+lane+r'=[^\n]+',s)[0]
  lines=[' // Match and prioritize broadcasts independently of late pair admission.']
  hits=[];terms=[]
  for source in ('f','f1','m','w','w1'):
   hit=f'inc_{lane}_hit_{source}';mask=f'inc_{lane}_use_{source}'
   lines.append(f' wire {hit}={source}_valid && tag_{lane}=={source}_tag;')
   prior=' || '.join(hits)
   lines.append(f' wire {mask}={hit}'+(f' && !({prior})' if prior else '')+';')
   hits.append(hit);terms.append('({32{'+mask+'}} & '+source+'_data)')
  lines.append(f' wire inc_{lane}_hit='+' || '.join(hits)+';')
  lines.append(f' wire[31:0] inc_{lane}_forward='+' | '.join(terms)+';')
  lines.append(f' wire[31:0] incoming_{lane}=wait_{lane} && inc_{lane}_hit ? inc_{lane}_forward : in_side[{bits}];')
  s=s.replace(old,'\n'.join(lines))
 p.write_text(s)
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=m['source_trial'],intent='Exact side incoming mux equivalence; prioritize F/F1/M/W/W1 without wait qualification, apply wait only at final data selection; no state/latency changes.'),indent=2)+'\n')
 print('PREPARED',dest.name)

if __name__=='__main__':main()
