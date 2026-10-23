"""Pair a standard low MUL with its dependent ADD, completing the ADD in MEM."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
def rep(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 manifest=ROOT/'docs/active_optimization_baseline.json';m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 for n,h in m['input_sha256'].items():assert hashlib.sha256((src/n).read_bytes()).hexdigest()==h,n
 dest=ROOT/'simulation/results/autonomous_20261022/mul_add_pair';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(manifest,dest/'parent_baseline.json')
 p=dest/'source/core/nc_core.v';s=p.read_text()
 s=rep(s,' wire pair_candidate=',''' // A dependent ADD can share the MUL retirement group. Its independent
 // addend must already be available; the MUL-produced operands do not wait
 // on an older writer to the same architectural register.
 wire muladd_raw_c=rd!=0 && rd==rs1_1,muladd_raw_d=rd!=0 && rd==rs2_1;
 wire id_muladd=id_mul_hint && id_insn[14:12]==0 &&
  id_insn1[31:25]==0 && id_insn1[14:12]==0 && id_insn1[6:0]==7'h33 &&
  (muladd_raw_c || muladd_raw_d) && (!dep_c || muladd_raw_c) && (!dep_d || muladd_raw_d);
 wire pair_candidate=''')
 s=rep(s,'!(id_mul_hint && (dep_c || dep_d))','!(id_mul_hint && (dep_c || dep_d) && !id_muladd)')
 s=rep(s,'!(id_pair_flags[2] && rd!=0 && ((id_pair_flags[5] && rd==rs1_1) || (id_pair_flags[6] && rd==rs2_1)))','!(id_pair_flags[2] && rd!=0 && ((id_pair_flags[5] && rd==rs1_1) || (id_pair_flags[6] && rd==rs2_1)) && !id_muladd)')
 s=rep(s,"id_prediction1,rd1,id_pair_flags[7],2'b0};","id_prediction1,rd1,id_pair_flags[7],(id_muladd && muladd_raw_c),(id_muladd && muladd_raw_d)};")
 s=rep(s,'.wait_c(pair_candidate && dep_c),.wait_d(pair_candidate && dep_d),','.wait_c(pair_candidate && dep_c && !(id_muladd && muladd_raw_c)),.wait_d(pair_candidate && dep_d && !(id_muladd && muladd_raw_d)),')
 s=rep(s,' wire side_multiply=',' wire side_muladd=ex_side[223] && |ex_side[1:0];\n wire side_multiply=')
 s=rep(s,"wire[31:0] side_value=side_branch ? secondary_result[212:181] : side_multiply ? 32'b0 : secondary_result[180:149];","wire[31:0] side_value=side_muladd ? (ex_side[1] ? ex_side[103:72] : ex_side[135:104]) : side_branch ? secondary_result[212:181] : side_multiply ? 32'b0 : secondary_result[180:149];")
 s=rep(s,'side_execute && !side_branch && !side_multiply && secondary_result','side_execute && !side_branch && !side_multiply && !side_muladd && secondary_result')
 s=rep(s,".packet(ex_side[203:0]),",".packet({ex_side[203:2],2'b0}),")
 p.write_text(s)
 p=dest/'source/core/nc_memory.v';s=p.read_text()
 old=' assign wb_side=secondary_multiply ? {held_side[64:32],mul_data} : held_side;'
 new=''' // ADD has no exception of its own. Both results remain owned by the
 // ordered MUL group and are captured together at the existing WB boundary.
 wire add_uses_mul_c=rd!=0 && held_side[51:47]==rd;
 wire add_uses_mul_d=rd!=0 && held_side[56:52]==rd;
 wire dependent_add=primary_multiply && f3==0 && held_side[64] &&
  held_side[63:57]==0 && held_side[46:44]==0 && held_side[38:32]==7'h33 &&
  (add_uses_mul_c || add_uses_mul_d);
 wire[31:0] dependent_sum=(add_uses_mul_c && add_uses_mul_d) ? {mul_data[30:0],1'b0} : mul_data+held_side[31:0];
 assign wb_side=dependent_add ? {held_side[64:32],dependent_sum} :
  secondary_multiply ? {held_side[64:32],mul_data} : held_side;'''
 s=rep(s,old,new);p.write_text(s)
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=m['source_trial'],intent='Standard MUL-low plus dependent ADD pairing; independent addend ready at issue, intra-pair WAW still excluded. Suppress premature side F1 broadcast; form ADD from registered MUL result and held addend at ordered MEM completion. Two normal retirement records; no ISA/software change.'),indent=2)+'\n')
 print('PREPARED',dest.name)
if __name__=='__main__':main()
