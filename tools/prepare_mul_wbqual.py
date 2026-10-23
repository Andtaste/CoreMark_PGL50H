"""Register WB forwarding qualifiers with WB payload to shorten measured paths."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'simulation/results/autonomous_20261022'
def main():
 src=WORK/'mul_predecode';dest=WORK/'mul_wbqual';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(src/'parent_baseline.json',dest/'parent_baseline.json')
 p=dest/'source/core/nc_core.v';s=p.read_text()
 for old,new in [
  (' wire wb_valid;wire[279:0] wb_packet;',' reg wb_forward0,wb_forward1;\n wire wb_valid;wire[279:0] wb_packet;'),
  ('.w1_valid(commit1 && w1_rd!=0)','.w1_valid(wb_forward1)'),
  ('.w_valid(commit && w_wr && w_rd!=0)','.w_valid(wb_forward0)')]:
  assert s.count(old)==1;s=s.replace(old,new)
 old=' always @(posedge clk) if(memory_done) begin wb_q<=memory_packet;wb_side_q<=memory_side;end'
 assert s.count(old)==1
 s=s.replace(old,old+'''
 // These qualifiers describe the payload captured by WB on the same edge.
 // Predecode destination/write/fault before WB rather than on its bypass path.
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin wb_forward0<=0;wb_forward1<=0;end
  else begin
   wb_forward0<=memory_done && !memory_packet[2] && memory_packet[3] && memory_packet[15:11]!=0;
   wb_forward1<=memory_done && !memory_packet[2] && memory_side[64] && !memory_side[38] && memory_side[43:39]!=0;
  end
 end''');p.write_text(s)
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial='mul_predecode',intent='Two WB qualifier flops, no new pipeline stage or bypass; cycle equivalent'),indent=2)+'\n')
 print('PREPARED mul_wbqual')
if __name__=='__main__':main()
