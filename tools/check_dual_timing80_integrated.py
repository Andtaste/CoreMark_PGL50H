"""Reuse exact module evidence; test the final physical UART configuration."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/load_bp_dual_boundary_uart';side=src.with_name('load_bp_dual_boundary_side');pair=src.with_name('load_bp_dual_boundary_pair');out=src/'integration';out.mkdir(exist_ok=True)
 inputs=[Path(__file__).resolve()];tests=[]
 for name in ('nc_core.v','nc_operands.v','nc_execute.v','nc_fetch.v','nc_btb.v','nc_csr.v','nc_stats.v','nc_memory.v','nc_mul_pipeline.v','nc_local_bus.v','nc_regfile.v'):
  assert sha(src/name)==sha(side/name);inputs +=[src/name,side/name]
 for name in ('top.v','nc_soc.v'):
  assert sha(src/name)==sha(pair/name);inputs +=[src/name,pair/name]
 tests +=['PASS final core and bus exact bytes equal fully regression-tested side; only SoC clock parameter and top CLOCK_HZ80 equal pair']
 for sub in ('checks','dual_checks','pair_checks','cancel_checks','audit_checks','memory_checks','address_contract','protocol','mul_protocol','timeline_checks','timing_equivalence','timing_proof'):
  p=side/sub/'result.json';x=json.loads(p.read_text());assert x['status']=='PASS';inputs.append(p);tests +=['PASS reuse exact module evidence: '+sub+' '+str(len(x['tests']))+' checks']
 base=ROOT/'tools/check_dual_timing80_uart.py';s=base.read_text().replace("'simulation/results/load_bp_dual_boundary_pair'","'simulation/results/load_bp_dual_boundary_uart'");ns={'__file__':str(base),'__name__':'uart80_integrated'};exec(compile(s,str(base),'exec'),ns);ns['main']();p=src/'uart80/result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__));p.write_text(json.dumps(x,indent=2)+'\n');inputs +=[base,p];tests +=['PASS final physical top exact 80MHz UART divisor and full frame']
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,scope='Module hash evidence reuse for unchanged architecture; final top separately elaborated. Final fixed-image tests and PDS are independent.',input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print('PASS integrated exact-source evidence')
if __name__=='__main__':main()
