"""Extend the existing M qualified-hit experiment to the two registered EX sources."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 accepted=ROOT/'docs/accepted_dual_baseline.json';d=json.loads(accepted.read_text());src=ROOT/'simulation/results/load_bp_dual_boundary_next_mqual';out=src.with_name('load_bp_dual_boundary_next_fqual');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v');c=(out/'nc_core.v').read_text();o=(out/'nc_operands.v').read_text()
 c=rep(c,' wire m_next_valid;', ''' wire next_f_valid=rst_n && ex_fire && !execute_packet[2] && execute_packet[3] && execute_packet[15:11]!=0 && execute_packet[7:4]!=4 && !ex_multiply;
 wire next_f1_valid=rst_n && ex_fire && side_execute && !side_branch && !side_multiply && secondary_result[15:11]!=0;
 wire m_next_valid;''')
 c=rep(c,'.next_m_valid(m_next_valid),','.next_f_valid(next_f_valid),.next_f1_valid(next_f1_valid),.next_m_valid(m_next_valid),')
 o=rep(o,' input wire next_m_valid,',' input wire next_f_valid,next_f1_valid,next_m_valid,')
 for op in 'abcd':
  for source,lane in [('f',0),('f1',1)]:
   o=rep(o,f's{source}_{op}[i]<=((push && wr==i[0]) ? tag_{op} : dep_{op}[i])=={{next_f_tag,1\'b{lane}}};',f's{source}_{op}[i]<=(((push && wr==i[0]) ? tag_{op} : dep_{op}[i])=={{next_f_tag,1\'b{lane}}}) && next_{source}_valid;')
   o=rep(o,f's{source}_{op}[s] && {source}_valid',f's{source}_{op}[s]')
 (out/'nc_core.v').write_text(c);(out/'nc_operands.v').write_text(o)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),accepted_dual_sha256=sha(accepted),trial='fqual',scope='M+F+F1 consumer-specific qualified hits at existing match FF boundary; no new operand cycle; independent accepted-baseline family; NOT ADOPTED')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',out.name)
if __name__=='__main__':main()
