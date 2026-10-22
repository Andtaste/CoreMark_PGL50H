"""Quote-safe injection into the historical Python-generated memory bench."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 base=ROOT/'tools/check_dual_store_prefix.py';ns={'__file__':str(base),'__name__':'prefix_contracts'};exec(compile(base.read_text(),str(base),'exec'),ns)
 # The historical adapter inserts this into a single-quoted Python literal.
 # Decimal Verilog constants avoid introducing the apostrophe in 32'h...
 ns['LOCAL']='(packet[148:117]<65536 || (packet[148:117]>=268435456 && packet[148:117]<268468224))'
 sys.argv=[str(base),'--mode','contracts'];ns['main']()
 for sub in ('memory_checks','address_contract'):
  p=ROOT/('simulation/results/load_bp_dual_boundary_storeprefix/'+sub+'/result.json');x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
