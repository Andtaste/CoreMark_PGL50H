"""Extend free-slot preload to metadata; late issue touches narrow validity only."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/load_bp_dual_boundary_preload';out=src.with_name('load_bp_dual_boundary_slots');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_operands.v';s=p.read_text();old='side[wr][223:136]<=in_side[223:136];side[wr][71:0]<=in_side[71:0];payload[wr]<=in_packet;controls[wr]<=in_control;token[wr]<=in_tag;dep_a[wr]<=tag_a;dep_b[wr]<=tag_b;\n   dep_c[wr]<=tag_c;dep_d[wr]<=tag_d;';assert s.count(old)==1;s=s.replace(old,'')
 assert s.count('predictions[wr]<=in_prediction;')==1;s=s.replace('predictions[wr]<=in_prediction;','')
 old='    va[i]<=incoming_a;vb[i]<=incoming_b;';assert s.count(old)==1;s=s.replace(old,'''    // Only unoccupied physical slots sample metadata. Push continues to
    // control count/wr/wait state, never widening into packet storage CE.
    side[i][223:136]<=in_side[223:136];side[i][71:0]<=in_side[71:0];
    payload[i]<=in_packet;controls[i]<=in_control;token[i]<=in_tag;
    dep_a[i]<=tag_a;dep_b[i]<=tag_b;dep_c[i]<=tag_c;dep_d[i]<=tag_d;
    predictions[i]<=in_prediction;
    va[i]<=incoming_a;vb[i]<=incoming_b;''');p.write_text(s)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope='dual_boundary_slots; empty slot data and metadata preload, issue changes narrow occupancy/identity-preparation/wait state; unchanged valid schedule; UART80 and PLL80 integrated; research not adopted')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED dual_boundary_slots')
if __name__=='__main__':main()
