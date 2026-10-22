"""Cancel an annulled branch-side producer before correct-path re-admission."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/load_bp_dual_joint_branch';out=src.with_name('load_bp_dual_joint_fix');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_core.v';s=p.read_text();old='   if(branch_redirect) begin';assert s.count(old)==1
 s=s.replace(old,old+'''\n    // Primary branch may annul a speculatively admitted ALU side while the
    // retirement group remains live. Its destination is no longer a producer.
    // Correct-path ID is blocked during redirect, so it sees this cancellation.
    destination1[redirect_tag]<=0;''');p.write_text(s)
 g['override_sha256']['hardware\\pds\\source\\core\\nc_core.v']=sha(p)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope='dual_joint_fix; joint slide/four-source capture plus primary and secondary conditional branch; clear annulled lane1 producer on registered branch redirect; no adoption')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED dual_joint_fix')
if __name__=='__main__':main()
