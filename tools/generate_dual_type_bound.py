"""Remove a redundant late side-MUL enable term under proved admission invariants."""
from pathlib import Path
import argparse,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_types_bound','dual_types_slide_bound'),required=True);a=ap.parse_args()
 parent='dual_types_slide' if 'slide' in a.variant else 'dual_types_compact'
 src=ROOT/('simulation/results/load_bp_'+parent);out=src.with_name('load_bp_'+a.variant);out.mkdir(exist_ok=True);g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h,n;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore',dirs_exist_ok=True);shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 s=(out/'nc_core.v').read_text();old='wire mul_accept=ex_fire && (ex_multiply || (side_multiply && side_execute));';assert s.count(old)==1
 s=s.replace(old,'''// A side MUL is admitted only with a legal ordinary ALU primary,
 // clean fetch, and no primary prediction. It cannot have a primary EX
 // fault/misprediction, so do not send that late comparison into DSP CE.
 wire mul_accept=ex_fire && (ex_multiply || side_multiply);''')
 (out/'nc_core.v').write_text(s);g['override_sha256']['hardware\\pds\\source\\core\\nc_core.v']=sha(out/'nc_core.v')
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope=a.variant+'; side MUL accept ends before primary branch/fault comparison; legal plain-primary admission invariant required and separately SAT checked')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',a.variant)
if __name__=='__main__':main()
