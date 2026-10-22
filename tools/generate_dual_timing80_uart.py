"""Keep the passed secondary specialization; integrate only board UART80 config."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/load_bp_dual_boundary_side';params=src.with_name('load_bp_dual_boundary_pair');out=src.with_name('load_bp_dual_boundary_uart');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text());assert json.loads((src/'pds/result.json').read_text())['status']=='PASS'
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 pg=json.loads((params/'generation.json').read_text())
 for n,h in pg['override_sha256'].items():
  if Path(n).name in ('nc_soc.v','top.v'):
   assert sha(params/Path(n).name)==h;shutil.copyfile(params/Path(n).name,out/Path(n).name);g['override_sha256'][n]=h
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),physical_config_generation_sha256=sha(params/'generation.json'),scope='dual_boundary_uart; passed side core unchanged, only explicit board CLOCK_HZ=80MHz integration from pair; pair annul shortcut excluded; research not adopted')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED dual_boundary_uart')
if __name__=='__main__':main()
