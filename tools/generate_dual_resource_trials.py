"""Lossless PC storage reductions from the accepted pairbranch source."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--trial',choices=('resourceside','resourcequeue','resourceboth','resourcecompare'),required=True);a=ap.parse_args()
 accepted=ROOT/'docs/accepted_dual_baseline.json';d=json.loads(accepted.read_text());assert d['variant']=='dual_boundary_next_pairbranch'
 src=ROOT/d['source_directory'];dest=src.with_name('load_bp_dual_boundary_next_'+a.trial);assert not dest.exists();dest.mkdir()
 g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,dest/p.name)
 shutil.copytree(src/'ipcore',dest/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',dest/'pango_ram_wide_models.v')
 c=(dest/'nc_core.v').read_text()
 if a.trial in ('resourceside','resourceboth'):
  c=rep(c,' wire[223:0] ex_side;', ''' // Side instruction PC is always main PC+4, including address wrap.
 // Reuse the main EX sequential-PC arithmetic instead of storing a second PC.
 wire[223:0] ex_side_stored;
 wire[223:0] ex_side={ex_side_stored[223:200],ex_packet[199:168]+32'd4,ex_side_stored[167:0]};''')
  c=rep(c,"id_side_kind,id_pc+32'd4,id_insn1", "id_side_kind,32'b0,id_insn1")
  c=rep(c,'.out_side(ex_side),','.out_side(ex_side_stored),')
 if a.trial in ('resourcequeue','resourceboth'):
  c=rep(c,' wire[31:0] queue_aux=execute_aux;', ''' // Branch next-PC already occupies the auxiliary word. Even on a
 // fetch/illegal branch, retain next-PC here; restore its fault auxiliary
 // from the independently stored PC/instruction at the MEM boundary.
 wire queue_branch=ex_packet[203:200]>=1 && ex_packet[203:200]<=3;
 wire[31:0] queue_aux=queue_branch ? execute_packet[212:181] : execute_aux;''')
  c=rep(c,' wire queued_valid,queue_credit;wire[248:0] queued_packet;', ''' wire queued_valid,queue_credit;wire[248:0] queued_packet;
 wire[216:0] queued_storage;
 wire queued_branch=queued_storage[7:4]>=1 && queued_storage[7:4]<=3;
 wire[31:0] queued_next=queued_branch ? queued_storage[52:21] : queued_storage[148:117]+32'd4;
 assign queued_packet={queued_storage[216:85],queued_next,queued_storage[84:0]};''')
  c=rep(c,'nc_fifo #(.WIDTH(249),.DEPTH(4)) memory_queue','nc_fifo #(.WIDTH(217),.DEPTH(4)) memory_queue')
  c=rep(c,'.in_data(incoming_packet),','.in_data({incoming_packet[248:117],incoming_packet[84:0]}),')
  c=rep(c,'.out_data(queued_packet));','.out_data(queued_storage));')
  c=rep(c,' wire[31:0] compact_value=compact_packet[84:53],compact_aux=compact_packet[52:21];', ''' wire[31:0] compact_value=compact_packet[84:53];
 wire[31:0] compact_aux=compact_packet[2] && compact_packet[20:16]==1 ? compact_packet[180:149] :
   compact_packet[2] && compact_packet[20:16]==2 ? compact_packet[148:117] : compact_packet[52:21];''')
 (dest/'nc_core.v').write_text(c)
 if a.trial=='resourcecompare':
  p=dest/'nc_execute.v';s=p.read_text()
  s=rep(s,' wire[31:0] selected_result=', ''' // Signed comparison shares the magnitude comparison with unsigned
 // comparison; differing signs select the sign of A. All inputs still
 // come from the same operand boundary; no new bypass or ready signal.
 wire alu_unsigned_less=a<rhs;
 wire alu_signed_less=(a[31]^rhs[31]) ? a[31] : alu_unsigned_less;
 wire branch_unsigned_less=a<b;
 wire branch_signed_less=(a[31]^b[31]) ? a[31] : branch_unsigned_less;
 wire[31:0] selected_result=''')
  s=rep(s,'{31\'b0,$signed(a)<$signed(rhs)}',"{31'b0,alu_signed_less}")
  s=rep(s,"{31'b0,a<rhs}","{31'b0,alu_unsigned_less}")
  s=rep(s,'4:taken=$signed(a)<$signed(b);','4:taken=branch_signed_less;')
  s=rep(s,'5:taken=$signed(a)>=$signed(b);6:taken=a<b;7:taken=a>=b;', '5:taken=!branch_signed_less;6:taken=branch_unsigned_less;7:taken=!branch_unsigned_less;')
  p.write_text(s)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(dest/Path(n).name)
 ips=[p for p in (dest/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),accepted_dual_sha256=sha(accepted),scope='Lossless PC resource compression from adopted pairbranch; NOT ADOPTED; unchanged FIFO depths, issue, bypass and clocks',trial=a.trial)
 (dest/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',dest.name)
if __name__=='__main__':main()
