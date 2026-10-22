"""Launch a ready primary load, retain its younger ALU at EX, commit atomically."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 accepted=ROOT/'docs/accepted_dual_baseline.json';d=json.loads(accepted.read_text());src=ROOT/d['source_directory'];out=src.with_name('load_bp_dual_boundary_next_loadsplitv2');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 c=(out/'nc_core.v').read_text();o=(out/'nc_operands.v').read_text();m=(out/'nc_memory.v').read_text()
 o=rep(o,' output wire occupied);',' output wire occupied,output wire primary_ready);')
 o=rep(o,' assign occupied=count!=0;', ' assign primary_ready=count!=0 && available_a[rd] && available_b[rd];\n assign occupied=count!=0;')
 c=rep(c,' wire ex_credit,ex_valid,',' wire primary_ready;reg split_phase,split_owner,split_done;reg[2:0] split_tag;reg[64:0] split_result;\n wire ex_credit,ex_valid,')
 c=rep(c,'.occupied(ex_occupied));','.occupied(ex_occupied),.primary_ready(primary_ready));')
 c=rep(c,' assign ex_pop=execute_ready && ex_enable;', ''' // Side execution is retained at the operand head, never reallocated.
 wire split_offer=primary_ready && !ex_valid && !split_owner && ex_enable &&
  ex_side[223] && ex_side[203:200]==0 && ex_packet[203:200]==4 && !ex_prediction[31];
 wire split_begin=split_offer && ex_fire;
 wire split_side_fire=split_phase && ex_valid && ex_enable;
 assign ex_pop=split_phase ? ex_enable : execute_ready && ex_enable;
 always @(posedge clk) begin
  if(split_begin) split_tag<=ex_tag;
  if(split_side_fire) split_result<=side_result;
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin split_phase<=0;split_owner<=0;split_done<=0;end
  else if(do_trap) begin split_phase<=0;split_owner<=0;split_done<=0;end
  else begin
   if(split_begin) begin split_phase<=1;split_owner<=1;split_done<=0;end
   if(split_side_fire) begin split_phase<=0;split_done<=1;end
   if(split_owner && memory_done && memory_packet[279:277]==split_tag) split_owner<=0;
   if(redirect) split_phase<=0;
  end
 end''')
 c=rep(c,'.valid(ex_valid && ex_enable),.ready(execute_ready)', '.valid((ex_valid || split_offer) && !split_phase && ex_enable),.ready(execute_ready)')
 c=rep(c,'wire side_execute=ex_side[223] && !execute_packet[2] && !prediction_wrong;', 'wire side_execute=ex_side[223] && !execute_packet[2] && !prediction_wrong && !split_offer;')
 c=rep(c,'always @(posedge clk) if(ex_fire) begin f1_data<=', 'always @(posedge clk) if(ex_fire || split_side_fire) begin f1_data<=')
 c=rep(c,'else f1_valid<=ex_fire && side_execute', 'else f1_valid<=(ex_fire || split_side_fire) && side_execute')
 c=rep(c,'memory(.side_packet(compact_side),', 'memory(.pending_valid(split_owner),.pending_tag(split_tag),.pending_done(split_done),.pending_side(split_result),.side_packet(compact_side),')
 m=rep(m,' input wire[64:0] side_packet,', ' input wire pending_valid,pending_done,input wire[2:0] pending_tag,input wire[64:0] pending_side,\n input wire[64:0] side_packet,')
 m=rep(m,' reg posted_response;', ' reg posted_response;reg saved_response;reg[31:0] saved_load;reg saved_error;')
 m=rep(m,' wire response=memory_pending && sent && rsp_valid && !posted_response;', ' wire raw_response=memory_pending && sent && rsp_valid && !posted_response && !saved_response;\n wire response=raw_response || saved_response;')
 m=rep(m,' wire response_error=response && rsp_error;', ' wire response_error=response && (saved_response ? saved_error : rsp_error);')
 m=rep(m,' wire complete=slot_valid &&', ' wire pending_match=pending_valid && pending_tag==tag;\n wire complete=(!pending_match || pending_done) && slot_valid &&')
 m=rep(m,'(memory_pending && sent && !kill);', '(memory_pending && sent && !kill && !saved_response);')
 m=rep(m,'assign wb_side=secondary_multiply ?', 'assign wb_side=pending_match ? pending_side : secondary_multiply ?')
 m=rep(m,'memory_access ? loaded :', 'memory_access ? (saved_response ? saved_load : loaded) :')
 m=rep(m,' // A detached accepted write is architectural', ''' always @(posedge clk) if(raw_response) begin saved_load<=loaded;saved_error<=rsp_error;end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) saved_response<=0;
  else if(kill || start || complete) saved_response<=0;
  else if(raw_response) saved_response<=1;
 end
 // A detached accepted write is architectural''')
 for name,s in (('nc_core.v',c),('nc_operands.v',o),('nc_memory.v',m)):(out/name).write_text(s)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),accepted_dual_sha256=sha(accepted),trial='loadsplit',scope='Independent ready-load + pending-side ALU execution split; one split owner; exact existing token/lane, ordered atomic retirement, buffered one-shot load response; NOT ADOPTED')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',out.name)
if __name__=='__main__':main()
