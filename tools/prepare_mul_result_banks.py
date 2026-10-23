"""Separate low/high completion writes to allow single-write LUT RAM result banks."""
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
 dest=WORK/'mul_result_banks';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):
  shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(manifest,dest/'parent_baseline.json')
 p=dest/'source/core/nc_mul_pipeline.v';s=p.read_text()
 changes={
 ' reg[31:0] results[0:7] /* synthesis syn_ramstyle="registers" */;':''' // Each bank has a single write port; low and high may complete together.
 reg[31:0] results_low[0:7] /* synthesis syn_ramstyle="lut_ram" */;
 reg[31:0] results_high[0:7] /* synthesis syn_ramstyle="lut_ram" */;
 reg[7:0] result_is_low;''',
 ' assign query_ready=available[query_tag];assign query_data=results[query_tag];':' assign query_ready=available[query_tag];\n assign query_data=result_is_low[query_tag] ? results_low[query_tag] : results_high[query_tag];',
 '  if(high_done) results[tag2]<=completed;':'  if(high_done) begin results_high[tag2]<=completed;result_is_low[tag2]<=0;end',
 '  if(low_done) results[tag1]<=low_completed;':'  if(low_done) begin results_low[tag1]<=low_completed;result_is_low[tag1]<=1;end',
 }
 for old,new in changes.items():
  assert s.count(old)==1,old
  s=s.replace(old,new)
 p.write_text(s)
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=m['source_trial'],intent='Separate single-write low/high result RAM banks with per-token selector; unchanged valid, latency, registered broadcast and consumption'),indent=2)+'\n')
 print('PREPARED',dest.name)

if __name__=='__main__':main()
