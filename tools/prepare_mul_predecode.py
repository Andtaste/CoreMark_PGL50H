"""Reuse the existing registered IF multiply class for the measured split policy."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'simulation/results/autonomous_20261022'
def main():
 src=WORK/'mul_split';dest=WORK/'mul_predecode';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(src/'parent_baseline.json',dest/'parent_baseline.json')
 p=dest/'source/core/nc_fetch.v';s=p.read_text();old='output wire[9:0] pair_flags,';assert s.count(old)==1
 s=s.replace(old,'output wire[9:0] pair_flags,output wire primary_multiply_hint,')
 old=' assign pair_flags={head_1[42],side_flags[3:0],pack_flags(head_0[42:34])};';assert s.count(old)==1
 s=s.replace(old,old+'\n // Existing registered classify_parts[7], not a new ID opcode decode.\n assign primary_multiply_hint=head_0[41];');p.write_text(s)
 p=dest/'source/core/nc_core.v';s=p.read_text();s=s.replace(' wire[9:0] id_pair_flags;',' wire id_mul_hint;wire[9:0] id_pair_flags;')
 s=s.replace('.pair_flags(id_pair_flags),','.primary_multiply_hint(id_mul_hint),.pair_flags(id_pair_flags),')
 old='wire pair_candidate=!(id_kind==6 && (dep_c || dep_d))';assert s.count(old)==1;s=s.replace(old,'wire pair_candidate=!(id_mul_hint && (dep_c || dep_d))');p.write_text(s)
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial='mul_split',intent='Equivalent split policy using already-registered legal multiply predecode; DIV is never pair eligible'),indent=2)+'\n')
 print('PREPARED mul_predecode')
if __name__=='__main__':main()
