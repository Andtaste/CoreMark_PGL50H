"""Clone the accepted core and optionally bypass the MUL result-table write."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_boundary_mulprobe','dual_boundary_multail','dual_boundary_mullowtail'),required=True);a=ap.parse_args();accepted=ROOT/'docs/accepted_dual_baseline.json';d=json.loads(accepted.read_text());assert d['variant']=='dual_boundary_storewrite';src=ROOT/d['source_directory'];out=src.with_name('load_bp_'+a.variant);assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 if not a.variant.endswith('mulprobe'):
  p=out/'nc_mul_pipeline.v';s=p.read_text();high='high_done && tag2==query_tag' if a.variant.endswith('multail') else "1'b0"
  s=rep(s,' assign query_ready=available[query_tag];assign query_data=results[query_tag];',f''' // Only the ordered MEM owner can consume a terminal completion early.
 // Existing registered F/M broadcasts to EX are unchanged. No ready feeds
 // this selection: terminal valid/tag come from multiplier pipeline FFs.
 wire query_low=low_done && tag1==query_tag;
 wire query_high={high};
 assign query_ready=available[query_tag] || query_low || query_high;
 assign query_data=query_low ? low_completed : query_high ? completed : results[query_tag];''')
  s=rep(s,'   if(high_done) available[tag2]<=1;', '   if(high_done && !(consume && query_tag==tag2)) available[tag2]<=1;');s=rep(s,'   if(low_done) available[tag1]<=1;', '   if(low_done && !(consume && query_tag==tag1)) available[tag1]<=1;');p.write_text(s)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),accepted_dual_sha256=sha(accepted),scope='Accepted storewrite clone; bench-only census or ordered MEM consumes terminal MUL completion before result-table write. EX broadcasts and all other RTL unchanged; not adopted')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',a.variant)
if __name__=='__main__':main()
