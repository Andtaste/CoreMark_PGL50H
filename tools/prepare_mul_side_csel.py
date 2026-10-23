"""Shorten the measured side ALU carry path, preserving the main ALU."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'simulation/results/autonomous_20261022'
def main():
 src=WORK/'mul_predecode';dest=WORK/'mul_side_csel';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(src/'parent_baseline.json',dest/'parent_baseline.json')
 p=dest/'source/core/nc_execute.v';s=p.read_text();old=" wire[31:0] add_value=a+(rhs^{32{control[13]}})+{31'b0,control[13]};";assert s.count(old)==1
 new=""" wire[31:0] add_value;
 generate if(ENABLE_DIV) begin:main_add
  assign add_value=a+(rhs^{32{control[13]}})+{31'b0,control[13]};
 end else begin:side_add
  wire[31:0] add_rhs=rhs^{32{control[13]}};
  wire[16:0] low={1'b0,a[15:0]}+{1'b0,add_rhs[15:0]}+control[13];
  wire[15:0] high0=a[31:16]+add_rhs[31:16];
  wire[15:0] high1=a[31:16]+add_rhs[31:16]+16'd1;
  assign add_value={low[16] ? high1 : high0,low[15:0]};
 end endgenerate"""
 p.write_text(s.replace(old,new))
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial='mul_predecode',intent='16+16 carry-select in secondary ALU only; cycle equivalent'),indent=2)+'\n')
 print('PREPARED mul_side_csel')
if __name__=='__main__':main()
