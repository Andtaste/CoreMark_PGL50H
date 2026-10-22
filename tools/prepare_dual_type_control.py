"""Byte-identical accepted RTL, separate benches for pairing type research."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/load_bp_dual_fwd_share';out=src.with_name('load_bp_dual_type_control');out.mkdir(exist_ok=True)
 g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h,n;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore',dirs_exist_ok=True);shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),scope='Accepted dual_fwd_share byte-identical profiling control; simulation counters only')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n')
if __name__=='__main__':main()
