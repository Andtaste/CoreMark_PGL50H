"""Count routed distributed RAMs and cross-check the PNR hierarchy report."""
from pathlib import Path
import collections,hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 source=ROOT/'simulation/results/load_bp_dual_if_parts/pds';dest=ROOT/'docs/dual_if/resource_audit';dest.mkdir(exist_ok=True)
 netlist=source/'place_route/top_pnr.netlist';report=source/'place_route/top.prr';mapping=source/'device_map/top.dmr'
 cells=re.findall(r'\nInst\n([^;\n]+);(gopRAM[^\n]+)',netlist.read_text());counts=collections.Counter()
 for n,t in cells:
  group='register_file' if '/rf/' in n else 'ex_mem_fifo' if '/memory_queue/' in n else 'btb' if '/predictor.btb' in n else 'instruction_fifo' if '/fetch/instructions' in n else 'other'
  counts[group]+=1
 assert dict(counts)==dict(instruction_fifo=64,btb=174,ex_mem_fifo=211,register_file=256),counts
 modules={}
 for line in report.read_text().splitlines():
  if not line.startswith('|'):continue
  cols=[x.strip() for x in line.split('|')]
  if len(cols)>6 and cols[2].isdigit():modules[cols[1].lstrip('+ ').strip()]=dict(lut=int(cols[2]),ff=int(cols[3]),distributed_ram=int(cols[4]),apm=int(cols[5]),drm=int(cols[6]))
 assert modules['rf']['distributed_ram']==counts['register_file']
 assert modules['memory_queue']['distributed_ram']==counts['ex_mem_fifo']
 assert modules['predictor.btb']['distributed_ram']+modules['predictor.btb1']['distributed_ram']==counts['btb']
 assert modules['fetch']['distributed_ram']-counts['btb']==counts['instruction_fifo']
 assert modules['top']['distributed_ram']==sum(counts.values())==705
 available=int(re.search(r'\| Distributed RAM\s+\|\s+705\s+\|\s+(\d+)',mapping.read_text())[1])
 x=dict(status='PASS',variant='dual_if_parts',routed_distributed_ram=dict(counts),total=705,available_resource_units=available,used_percent=705/available*100,
  final_resources=modules['top'],source='Actual routed operator count, independently checked against per-module PNR utilization; not the pre-map inferred RAM table.',
  input_sha256={str(p.relative_to(ROOT)):sha(p) for p in (netlist,report,mapping,Path(__file__).resolve())},
  vendor_architecture_reference='https://www.pangomicro.com/en/uploads/43087615_1711095655.pdf',
  accounting_limit='Distributed RAM and LUT rows are separate PDS metrics; do not infer physical LUT occupancy by simply adding the counts.')
 (dest/'result.json').write_text(json.dumps(x,indent=2)+'\n');shutil.copyfile(report,dest/'top.prr')
 print(json.dumps({k:v for k,v in x.items() if k!='input_sha256'},indent=2))
if __name__=='__main__':main()
