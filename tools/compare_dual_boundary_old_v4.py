"""Honor old IF's two adjacent words from any aligned word address."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 base=ROOT/'tools/compare_dual_boundary_old_v3.py';s=base.read_text()
 needle='  corefiles=[]' # Directory substitution is inside the generated runner.
 s=s.replace("s=base.read_text().replace(\"('old','fifo','slot','early')\",\"('old','fifo','slot','early','read')\")", "s=base.read_text().replace(\"('old','fifo','slot','early')\",\"('old','fifo','slot','early','read')\").replace('dual_boundary_common','dual_boundary_common_v4')")
 needle=" bus=out/'nc_local_bus_common.v';bus.write_text(bs);inputs +=[original_bus]"
 verilog=" reg[63:0] common_fetch;\n always @(posedge clk) if(ia_fire) begin\n  if(ib0) common_fetch<={ram_code.mem[ia[15:2]+14'd1],ram_code.mem[ia[15:2]]};\n  else if(ib1) common_fetch<={ram_data.mem[ia[14:2]+13'd1],ram_data.mem[ia[14:2]]};\n  else common_fetch<=0;\n end\n"
 repl=" bs=bs.replace('assign idata=ibank ? iq1 : iq0;','assign idata=common_fetch;').replace(' reg mmio_known;',"+repr(verilog)+"+' reg mmio_known;')\n"+needle
 marker=' assert s.count(needle)==1;s=s.replace(needle,code+needle)'
 assert s.count(marker)==1
 s=s.replace(marker, ' code=code.replace('+repr(needle)+','+repr(repl)+')\n'+marker)
 s=s.replace("p=ROOT/('simulation/results/dual_boundary_common/'+v+'/result.json')", "p=ROOT/('simulation/results/dual_boundary_common_v4/'+v+'/result.json')")
 ns={'__file__':str(base),'__name__':'common_v4'};exec(compile(s,str(base),'exec'),ns);ns['main']()
 v=sys.argv[sys.argv.index('--target')+1];p=ROOT/('simulation/results/dual_boundary_common_v4/'+v+'/result.json');x=json.loads(p.read_text());x['scope']='Same binary; common behavioral service with word-aligned two-adjacent-word IF snapshot and explicit atomic old dual-LSU acceptance. Not a physical A64 RAM implementation or original SoC comparison.';x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
