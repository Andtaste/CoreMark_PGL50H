"""Keep read request payload stable when ownership moves EX -> MEM under stall."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/load_bp_dual_boundary_load';out=src.with_name('load_bp_dual_boundary_read');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_memory.v';s=p.read_text();s=s.replace("assign req_data=store_data << {address[1:0],3'b0};", "assign req_data=req_write ? (store_data << {address[1:0],3'b0}) : 32'b0;")
 s=s.replace("assign req_mask=f3[1:0]==0 ? (4'b1<<address[1:0]) : f3[1:0]==1 ? (4'b11<<address[1:0]) : 4'b1111;", "assign req_mask=!req_write ? 4'b1111 : f3[1:0]==0 ? (4'b1<<address[1:0]) : f3[1:0]==1 ? (4'b11<<address[1:0]) : 4'b1111;");p.write_text(s)
 g['override_sha256']['hardware\\pds\\source\\core\\nc_memory.v']=sha(p)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope='dual_boundary_read; load-only early launch/prepared five-source identity; constant ignored read write-data/mask preserve full request stability across EX/MEM ownership; registered stores; no raw load return; not adopted')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED dual_boundary_read')
if __name__=='__main__':main()
