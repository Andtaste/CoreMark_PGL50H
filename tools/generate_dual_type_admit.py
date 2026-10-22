"""End side admission at registered predecode flags, not full decode illegal/write paths."""
from pathlib import Path
import argparse,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_types_admit','dual_types_slide_admit'),required=True);a=ap.parse_args()
 parent='dual_types_slide_bound' if 'slide' in a.variant else 'dual_types_bound'
 src=ROOT/('simulation/results/load_bp_'+parent);out=src.with_name('load_bp_'+a.variant);out.mkdir(exist_ok=True);g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h,n;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore',dirs_exist_ok=True);shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 s=(out/'nc_core.v').read_text()
 for old,new in (('id1_kind==1 || !id_prediction1[31]','id_insn1[6] || !id_prediction1[31]'),('id_pair_flags[2] && id1_wr && rd!=0','id_pair_flags[2] && id_pair_flags[7] && rd!=0'),('pair_candidate && id1_wr ? rd1 : 0','pair_candidate && id_pair_flags[7] ? rd1 : 0'),("id_prediction1,rd1,id1_wr,2'b0","id_prediction1,rd1,id_pair_flags[7],2'b0")):
  assert s.count(old)==1,(old,s.count(old));s=s.replace(old,new)
 (out/'nc_core.v').write_text(s);g['override_sha256']['hardware\\pds\\source\\core\\nc_core.v']=sha(out/'nc_core.v')
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope=a.variant+'; all pairing type/write gating uses registered predecode and admitted opcode identity; full decode only feeds existing ID/EX payload registers')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',a.variant)
if __name__=='__main__':main()
