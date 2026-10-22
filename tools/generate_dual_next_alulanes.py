"""Allow return-to-ALU independently per lane, retaining separate AGU/branch data."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 accepted=ROOT/'docs/accepted_dual_baseline.json';src=ROOT/'simulation/results/load_bp_dual_boundary_next_aluwake';out=src.with_name('load_bp_dual_boundary_next_alulanes');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v');o=(out/'nc_operands.v').read_text()
 o=rep(o,'wire[1:0] alu_return;','wire[1:0] primary_return,secondary_return;')
 o=rep(o,'assign alu_return[s]=payload[s][203:200]==0 && (!side[s][223] || side[s][203:200]==0);','assign primary_return[s]=payload[s][203:200]==0;\n  assign secondary_return[s]=side[s][203:200]==0;')
 o=o.replace('// Current-cycle return eligibility is restricted to ALU-only groups.','// Each lane permits return data for its ALU independently of its partner.')
 for op in 'abcd':
  enable='primary_return' if op in 'ab' else 'secondary_return'
  o=rep(o,f'wire alu_r_{op}=alu_return[s]',f'wire alu_r_{op}={enable}[s]')
  o=rep(o,f'out_alu_{op}=(w{op}[rd] && alu_return[rd]',f'out_alu_{op}=(w{op}[rd] && {enable}[rd]')
 (out/'nc_operands.v').write_text(o)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),accepted_dual_sha256=sha(accepted),trial='alulanes',scope='Independent per-lane ALU return eligibility, without requiring the partner to be ALU; inherited physically separate ALU data ports and original AGU/branch/CSR operands; NOT ADOPTED')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',out.name)
if __name__=='__main__':main()
