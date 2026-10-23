"""Register a redundant architectural busy summary for multiply pair admission."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
def main():
 manifest=ROOT/'docs/active_optimization_baseline.json'
 m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 for n,h in m['input_sha256'].items():assert hashlib.sha256((src/n).read_bytes()).hexdigest()==h,n
 dest=ROOT/'simulation/results/autonomous_20261022/pair_busy';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(manifest,dest/'parent_baseline.json')
 p=dest/'source/core/nc_core.v';s=p.read_text()
 old=' wire pair_candidate=!(id_mul_hint && (dep_c || dep_d))'
 assert s.count(old)==1
 s=s.replace(old,''' // Redundant registered summary; youngest-writer tags still use the ledger.
 reg[31:0] pair_busy;
 reg[31:0] pair_busy_next;
 reg busy_live_next;reg[4:0] busy_rd0,busy_rd1;integer bi;
 always @* begin
  pair_busy_next=0;busy_live_next=0;busy_rd0=0;busy_rd1=0;
  for(bi=0;bi<8;bi=bi+1) begin
   busy_live_next=(live[bi] && !(wb_valid && w_tag==bi)) || (issue && tail==bi);
   busy_rd0=(issue && tail==bi) ? (id_wr ? rd : 5'b0) : destination[bi];
   busy_rd1=(issue && tail==bi) ? (pair_candidate && id_pair_flags[7] ? rd1 : 5'b0) : destination1[bi];
   if(branch_redirect) begin
    if(((bi-head)&7)>((redirect_tag-head)&7)) busy_live_next=0;
    if(redirect_tag==bi) busy_rd1=0;
   end
   if(busy_live_next) begin
    if(busy_rd0!=0) pair_busy_next[busy_rd0]=1;
    if(busy_rd1!=0) pair_busy_next[busy_rd1]=1;
   end
  end
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) pair_busy<=0;
  else if(do_trap || irq_take) pair_busy<=0;
  else pair_busy<=pair_busy_next;
 end
 wire pair_dep_c=id_pair_flags[5] && pair_busy[rs1_1];
 wire pair_dep_d=id_pair_flags[6] && pair_busy[rs2_1];
 wire pair_candidate=!(id_mul_hint && (pair_dep_c || pair_dep_d))''')
 p.write_text(s)
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=m['source_trial'],intent='Registered redundant busy bitmap used only for main-multiply pair admission; preserve original tag priority, source waits, issue and retirement rules. Next bitmap mirrors commit/issue/branch-side annul/younger squash/trap state transitions.'),indent=2)+'\n')
 print('PREPARED',dest.name)
if __name__=='__main__':main()
