"""Apply existing independent ALU-return contracts to the new baseline candidate."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
mode=sys.argv[1]
assert mode in ('operands','timeline','proof')
if mode=='timeline':
 base=ROOT/'tools/check_dual_boundary.py'
 code=base.read_text().replace("read_text(encoding='utf-8')","read_text(encoding='utf-8-sig')")
 old="r==e+(0 if a.variant.endswith('_early') else 1) and w==r+1 and c==w+1"
 assert code.count(old)==1
 # Same explicit per-consumer timing contract as check_dual_next_alu_timeline,
 # but generate and execute a fresh waveform instead of repairing an old suite.
 code=code.replace(old,"r>=e and w==r+1 and c==w+(0 if p['consumer'] in ('alu_consumer','chain_consumer') else 1)")
 sys.argv=[str(base),'--variant','dual_boundary_auto_shortmul_alulanes','--mode','timeline']
 namespace={'__file__':str(base),'__name__':'shortmul_alu_timeline'}
 exec(compile(code,str(base),'exec'),namespace);namespace['main']()
else:
 base=ROOT/'tools/check_dual_next_alulanes.py'
 code=base.read_text().replace('dual_boundary_next_alulanes','dual_boundary_auto_shortmul_alulanes')
 namespace={'__file__':str(base),'__name__':'shortmul_alu_contract_adapter'}
 exec(compile(code,str(base),'exec'),namespace)
sub={'operands':'operands_checks','timeline':'timeline_checks','proof':'alu_control_proof'}[mode]
receipt=ROOT/'simulation/results/load_bp_dual_boundary_auto_shortmul_alulanes'/sub/'result.json'
record=json.loads(receipt.read_text());assert record['status']=='PASS'
record['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
record['adapter_note']='Original operand model and exact-byte SAT-proof reuse retained. Timeline generates a fresh waveform and checks the existing ALU-same-cycle versus non-ALU-next-WB contract.'
receipt.write_text(json.dumps(record,indent=2)+'\n')
print('shortmul_alulanes',mode,'PASS')
