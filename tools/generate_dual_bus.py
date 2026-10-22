"""Isolate RAM collision authorization; optionally distribute bank enables."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_bus_split','dual_bus_local'),required=True);a=ap.parse_args()
 src=ROOT/'simulation/results/load_bp_dual_ram_logic';dest=src.with_name('load_bp_'+a.variant);dest.mkdir(exist_ok=True)
 meta=json.loads((src/'generation.json').read_text())
 for n,h in meta['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h,n;shutil.copyfile(p,dest/p.name)
 for n,h in meta['ip_sha256'].items():assert sha(ROOT/n)==h,n
 shutil.copytree(src/'ipcore',dest/'ipcore',dirs_exist_ok=True)
 shutil.copyfile(src/'pango_ram_wide_models.v',dest/'pango_ram_wide_models.v')
 p=dest/'nc_local_bus.v';s=p.read_text()
 s=rep(s,' wire da_fire=dv && dr;',''' wire da_fire=dv && dr;
 // RAM addresses cannot be UART MMIO. Keep UART busy out of the
 // cross-port collision permission cone; no new cycle or request bypass.
 wire data_slot=rst_n && (!dpending || dor);
 wire ram_write_offer=dv && data_slot && dwrite;''')
 old=' wire collision=da_fire && dwrite && ((ib0 && db0)||(ib1 && db1)) && ia[15:3]==da[15:3];'
 if a.variant=='dual_bus_split':
  s=rep(s,old,' wire collision=ram_write_offer && ((ib0 && db0)||(ib1 && db1)) && ia[15:3]==da[15:3];')
 else:
  s=rep(s,old,''' wire same_row=ia[15:3]==da[15:3];
 wire collision0=ram_write_offer && db0 && same_row;
 wire collision1=ram_write_offer && db1 && same_row;
 wire collision=(ib0 && collision0) || (ib1 && collision1);
 wire fetch_slot=rst_n && (!ipending || ior);
 // Bank-local RAM controls avoid the common global ia_fire/collision
 // round trip. The architectural IF acceptance still uses exact collision.
 wire ia0_fire=iv && fetch_slot && ib0 && !collision0 && !ia[1] && !ia[0];
 wire ia1_fire=iv && fetch_slot && ib1 && !collision1 && !ia[1] && !ia[0];
 wire da0_fire=dv && data_slot && db0;
 wire da1_fire=dv && data_slot && db1;''')
  s=rep(s,'assign ir=rst_n && (!ipending || ior) && !collision;','assign ir=fetch_slot && !collision;')
  for old,new in (('ia_fire && ib0 && !ia[1] && !ia[0]','ia0_fire'),('ia_fire && ib1 && !ia[1] && !ia[0]','ia1_fire'),('da_fire && db0','da0_fire'),('da_fire && db1','da1_fire')):s=rep(s,old,new)
 p.write_text(s)
 for n in meta['override_sha256']:meta['override_sha256'][n]=sha(dest/Path(n).name)
 ips=[p for p in (dest/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 meta['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[src/'boot_interleaved.hex']}
 meta.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope=a.variant+'; identical issue policy, IP contents, cycles and FIFO boundaries')
 (dest/'generation.json').write_text(json.dumps(meta,indent=2)+'\n');print('GENERATED',a.variant)
if __name__=='__main__':main()
