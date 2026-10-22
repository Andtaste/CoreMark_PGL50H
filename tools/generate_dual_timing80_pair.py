"""Specialize paired-primary annul qualification; board wrapper uses PLL80/UART80."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 src=ROOT/'simulation/results/load_bp_dual_boundary_side';out=src.with_name('load_bp_dual_boundary_pair');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 accepted=ROOT/'docs/accepted_dual_baseline.json';assert g['accepted_dual_sha256']==sha(accepted)
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_core.v';s=p.read_text();s=rep(s,' wire side_execute=ex_side[223] && !execute_packet[2] && !prediction_wrong;', ''' // A paired primary is never JAL/JALR, and pair admission requires a
 // not-taken prediction. Its only possible prediction correction is a
 // taken conditional branch with an immediate other than four. Keep
 // this narrow annul predicate off the unrelated indirect AGU comparator.
 // The primary fault still cancels its secondary independently.
 wire pair_primary_wrong=ex_control[16] && execute_taken && ex_packet[71:40]!=32'd4;
 wire side_execute=ex_side[223] && !execute_packet[2] && !pair_primary_wrong;''');p.write_text(s)
 p=out/'nc_soc.v';s=p.read_text();s=rep(s,'module nc_soc(input wire','module nc_soc #(parameter CLOCK_HZ=75000000)(input wire');s=rep(s,' nc_local_bus bus(', ' nc_local_bus #(.CLOCK_HZ(CLOCK_HZ)) bus(');p.write_text(s)
 top=ROOT/'hardware/pds/source/source/top.v';p=out/'top.v';s=rep(top.read_text(),' nc_soc soc(', ' nc_soc #(.CLOCK_HZ(80000000)) soc(');p.write_text(s);g['override_sha256'][str(top.relative_to(ROOT))]=sha(p)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope='dual_boundary_pair; secondary jump constants plus paired-primary narrow annul predicate; physical top explicitly configures UART80 with isolated PLL80; simulation SoC default remains75 to compare fixed images; research not adopted')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED dual_boundary_pair')
if __name__=='__main__':main()
