"""Keep unformatted LW return forwarding; LB/LH retain the WB boundary."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/load_bp_dual_legacy_return';out=src.with_name('load_bp_dual_legacy_word');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_memory.v';s=p.read_text();a='&& kind==4 && wr && rd!=0;';assert s.count(a)==1;s=s.replace(a,'&& kind==4 && load_word && wr && rd!=0;');s=s.replace('assign return_data=loaded;','assign return_data=rsp_data;');p.write_text(s)
 g['override_sha256']['hardware\\pds\\source\\core\\nc_memory.v']=sha(p)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope='dual_legacy_word; eight-word banked FIFO, branch/MUL and both-lane source bypass; only naturally aligned LW returns bypass WB, LB/LH still wait WB; raw data avoids MEM subword formatter; registered request/ready boundaries unchanged; no adoption')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED dual_legacy_word')
if __name__=='__main__':main()
