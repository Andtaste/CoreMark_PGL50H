"""Clone the accepted baseline for isolated MEM/IPC profiling and trials."""
from pathlib import Path
import hashlib,json,shutil,argparse
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',default='dual_boundary_memprobe');a=ap.parse_args();assert a.variant=='dual_boundary_memprobe'
 accepted=ROOT/'docs/accepted_dual_baseline.json';d=json.loads(accepted.read_text(encoding='utf-8'));assert d['variant']=='dual_boundary_slots';src=ROOT/d['source_directory'];out=src.with_name('load_bp_'+a.variant);assert not out.exists();out.mkdir()
 g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.pop('reused_operand_sha256',None);g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),accepted_dual_sha256=sha(accepted),scope='Exact accepted slots RTL and PLL80/UART80, observation only; no adoption change')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED '+a.variant)
if __name__=='__main__':main()
