"""Precompute static intra-pair register conflicts at cached fetch-head updates."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
def rep(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 manifest=ROOT/'docs/active_optimization_baseline.json'
 m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 for n,h in m['input_sha256'].items():assert hashlib.sha256((src/n).read_bytes()).hexdigest()==h,n
 dest=ROOT/'simulation/results/autonomous_20261022/fetch_pair_conflict';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(manifest,dest/'parent_baseline.json')
 p=dest/'source/core/nc_core.v';s=p.read_text()
 s=rep(s,' wire id_mul_hint;',' wire id_pair_conflict;\n wire id_mul_hint;')
 s=rep(s,'.primary_multiply_hint(id_mul_hint),','.pair_conflict(id_pair_conflict),.primary_multiply_hint(id_mul_hint),')
 old='!second_dep && !(id_pair_flags[2] && rd!=0 && ((id_pair_flags[5] && rd==rs1_1) || (id_pair_flags[6] && rd==rs2_1))) &&\n  !(id_pair_flags[2] && id_pair_flags[7] && rd!=0 && rd==rd1);'
 s=rep(s,old,'!second_dep && !id_pair_conflict;');p.write_text(s)
 p=dest/'source/core/nc_fetch.v';s=p.read_text()
 s=rep(s,' output wire[9:0] pair_flags,output wire primary_multiply_hint,',' output wire[9:0] pair_flags,output wire primary_multiply_hint,output reg pair_conflict,')
 needle=' always @(posedge clk) begin\n  if(even_write)'
 replacement=''' // These flags depend only on the two cached words, never on live producers.
 function static_pair_conflict;
  input[106:0] first_word,second_word;
  begin static_pair_conflict=first_word[36] && first_word[11:7]!=0 &&
   ((second_word[34] && first_word[11:7]==second_word[19:15]) ||
    (second_word[35] && first_word[11:7]==second_word[24:20]) ||
    (second_word[36] && first_word[11:7]==second_word[11:7]));end
 endfunction
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) pair_conflict<=0;
  else if(consume) pair_conflict<=pop_two ?
   static_pair_conflict(after_two_0,after_two_1) : static_pair_conflict(after_one_0,after_one_1);
  else if(push && count<2) pair_conflict<=count==0 ?
   static_pair_conflict(in0,flight_two ? in1 : 107'b0) : static_pair_conflict(head_0,in0);
 end
 always @(posedge clk) begin
  if(even_write)'''
 s=rep(s,needle,replacement);p.write_text(s)
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=m['source_trial'],intent='Register static intra-pair RAW/WAW rejection alongside cached IF heads, with precomputed one/two-pop alternatives; preserve live dependency/tag selection and all head/count updates.'),indent=2)+'\n')
 print('PREPARED',dest.name)
if __name__=='__main__':main()
