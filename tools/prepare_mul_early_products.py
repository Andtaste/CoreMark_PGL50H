"""Evaluate capturing DSP partial products directly on multiplier acceptance."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'simulation/results/autonomous_20261022'

def main():
 manifest=ROOT/'docs/active_optimization_baseline.json'
 m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 for name,digest in m['input_sha256'].items():
  assert hashlib.sha256((src/name).read_bytes()).hexdigest()==digest,name
 dest=WORK/'mul_early_products';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):
  shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(manifest,dest/'parent_baseline.json')
 p=dest/'source/core/nc_mul_pipeline.v';s=p.read_text()
 changes={
 ' reg lane0,lane1,lane2;reg v0,v1,v2;reg[2:0] tag0,tag1,tag2;reg[1:0] op0,op1,op2;':' reg lane1,lane2;reg v1,v2;reg[2:0] tag1,tag2;reg[1:0] op1,op2;',
 ' reg[31:0] aa,bb;':' wire[31:0] aa=a,bb=b;wire[1:0] op0=operation;',
 ' assign busy=v0 || v1 || (v2 && op2!=0) || |available;':' assign busy=v1 || (v2 && op2!=0) || |available;',
 '  if(accept) begin lane0<=in_lane;aa<=a;bb<=b;op0<=operation;tag0<=in_tag;end\n  if(v0) begin lane1<=lane0;p_ll<=ll;p_lh<=lh;p_hl<=hl;p_hh<=hh;op1<=op0;tag1<=tag0;end':'  // Capture partial products immediately; token ownership follows acceptance.\n  if(accept) begin lane1<=in_lane;p_ll<=ll;p_lh<=lh;p_hl<=hl;p_hh<=hh;op1<=operation;tag1<=in_tag;end',
 '   v0<=accept;v1<=v0;v2<=v1;':'   v1<=accept;v2<=v1;',
 }
 for old,new in changes.items():
  assert s.count(old)==1,old
  s=s.replace(old,new)
 assert s.count('v0<=0;')==2;s=s.replace('v0<=0;','')
 s=s.replace('// FFs permit Pango APM input/output-register packing. Completion is buffered','// Partial products are captured on acceptance. Completion is buffered')
 s=s.replace('// Fixed-latency, one-input-per-cycle multiply datapath. Input and product','// Fixed-latency, one-input-per-cycle multiply datapath.')
 p.write_text(s)
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=m['source_trial'],intent='Remove multiplier input register stage; low/high completion each one cycle earlier; retain token buffer and low-priority collision arbitration behavior'),indent=2)+'\n')
 print('PREPARED',dest.name)

if __name__=='__main__':main()
