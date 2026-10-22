"""Normalize async flops for the MEM equivalence SAT backend."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
 base=ROOT/'tools/check_dual_store_simple.py';s=base.read_text();assert s.count('proc; memory; equiv_make')==1;s=s.replace('proc; memory; equiv_make','proc; memory; async2sync; equiv_make');ns={'__file__':str(base),'__name__':'logic_equivalence'};exec(compile(s,str(base),'exec'),ns);sys.argv=[str(base),'--variant','dual_boundary_storelogic','--mode','proof'];ns['main']()
 p=ROOT/'simulation/results/load_bp_dual_boundary_storelogic/simple_proof/result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
