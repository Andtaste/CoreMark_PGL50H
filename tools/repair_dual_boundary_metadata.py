"""Recover only postprocessing after a Windows log-decoding error; do not rerun RTL."""
from pathlib import Path
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
 v=sys.argv[1];src=ROOT/('simulation/results/load_bp_'+v);phase=sys.argv[2];t=(src/phase/'simulation.log').read_text(errors='replace');assert 'COUNTER_CHECK_PASS' in t and 'PASS cycles=' in t
 m=re.search(r'BOUNDARY_WINDOW ([^\r\n]+)',t);assert m;b={k:int(x) for k,x in re.findall(r'(\w+)=(\d+)',m[1])}
 for p in [src/phase/'result.json']+([src/'result.json'] if phase=='performance' else []):
  x=json.loads(p.read_text(encoding='utf-8'));assert x['status']=='PASS';x['variant']=v;x['boundary']=b;x['scope']='Uniform MEM ownership and empty spill-FIFO handoff; optional EX-edge local request; no raw RAM/EX bypass; not adopted'
  for n in (Path(__file__),ROOT/'tools/run_dual_boundary.py',ROOT/'tools/run_dual_boundary_v2.py',ROOT/'tools/generate_dual_boundary.py'):x['input_sha256'][str(n.relative_to(ROOT))]=hashlib.sha256(n.read_bytes()).hexdigest()
  x['postprocess_note']='Original functional run and independent counters passed. Recovered boundary counters after Windows GBK decoding failed on binary UART bytes; RTL and simulation logs unchanged.'
  p.write_text(json.dumps(x,indent=2)+'\n')
 print(v,phase,b)
if __name__=='__main__':main()
