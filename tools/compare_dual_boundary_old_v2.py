"""Include the frozen old RF's utility flip-flop dependency."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
 base=ROOT/'tools/compare_dual_boundary_old.py';s=base.read_text();needle="  cp='''tinyriscv_core cpu"
 replacement="  p=old/'source/utils/gen_dff.v';assert sha(p)==hashes['utils/gen_dff.v'];q=snap/p.name;shutil.copyfile(p,q);corefiles.append(q);inputs +=[p,q]\n"+needle
 assert s.count(needle)==1;s=s.replace(needle,replacement);ns={'__file__':str(base),'__name__':'old_compare_v2'};exec(compile(s,str(base),'exec'),ns);ns['main']()
 target=sys.argv[sys.argv.index('--target')+1];p=ROOT/('simulation/results/dual_boundary_common/'+target+'/result.json');x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
