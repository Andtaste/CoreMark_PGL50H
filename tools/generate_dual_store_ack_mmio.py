"""Use the already-registered MEM control address for all MMIO decode."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/load_bp_dual_boundary_storeack';out=src.with_name('load_bp_dual_boundary_storemmio');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text());assert g['accepted_dual_sha256']==sha(ROOT/'docs/accepted_dual_baseline.json')
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_local_bus.v';s=p.read_text();assert s.count('case(da)')==2;s=s.replace('case(da)','case(wa)');assert s.count("if(da==32'h20002000")==1;s=s.replace("if(da==32'h20002000","if(wa==32'h20002000")
 s=s.replace(' reg mmio_known;', ''' // wa is the registered MEM address, also used by published writes.
 // All valid nonlocal requests are MEM-owned and must satisfy wa==da.
 // Early EX requests are local RAM reads only; their wa/MMIO data is ignored.
 // Keep their late AGU out of MMIO value/decode and wide write enables.
 reg mmio_known;''');p.write_text(s)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope='Same storeack schedule; registered MEM address drives MMIO read/write decode, valid nonlocal request invariant wa==da required and checked; no change to local RAM address/data interface; research not adopted')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED dual_boundary_storemmio')
if __name__=='__main__':main()
