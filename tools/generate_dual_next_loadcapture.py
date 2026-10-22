"""Capture formatted load return at the existing operand FFs, no same-cycle EX use."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 accepted=ROOT/'docs/accepted_dual_baseline.json';d=json.loads(accepted.read_text());src=ROOT/d['source_directory'];out=src.with_name('load_bp_dual_boundary_next_loadcapture');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 c=(out/'nc_core.v').read_text();o=(out/'nc_operands.v').read_text();m=(out/'nc_memory.v').read_text()
 m=rep(m,'input wire rsp_error);','input wire rsp_error,\n output wire return_valid,output wire[2:0] return_tag,output wire[31:0] return_data);')
 m=rep(m,' wire[31:0] completed_result=',' assign return_valid=wb_valid && !exception && !response_error && kind==4 && wr && rd!=0;\n assign return_tag=tag;assign return_data=loaded;\n wire[31:0] completed_result=')
 c=rep(c,' wire m_valid,m_lane;',' wire r_valid;wire[2:0] r_tag;wire[31:0] r_data;\n wire m_valid,m_lane;')
 c=rep(c,'.m_valid(m_valid),.m_tag({m_tag,m_lane}),.m_data(m_data),','.m_valid(m_valid),.m_tag({m_tag,m_lane}),.m_data(m_data),\n  .r_valid(r_valid),.r_tag({r_tag,1\'b0}),.r_data(r_data),')
 c=rep(c,'.wb_valid(memory_done),.wb_packet(memory_packet),','.return_valid(r_valid),.return_tag(r_tag),.return_data(r_data),\n  .wb_valid(memory_done),.wb_packet(memory_packet),')
 o=rep(o,' input wire m_valid,input wire[3:0] m_tag,input wire[31:0] m_data,',' input wire m_valid,input wire[3:0] m_tag,input wire[31:0] m_data,\n input wire r_valid,input wire[3:0] r_tag,input wire[31:0] r_data,')
 for op in 'abcd':
  storage={'a':'va[i]','b':'vb[i]','c':'side[i][135:104]','d':'side[i][103:72]'}[op];selected={'a':'selected_va[i]','b':'selected_vb[i]','c':'selected_c[i]','d':'selected_d[i]'}[op]
  hit=f'(r_valid && r_tag==dep_{op}[i])'
  higher=f'(hit_f{op}[i] || hit_f1{op}[i] || hit_m{op}[i])' if op in 'ab' else f'((sf_{op}[i] && f_valid) || (sf1_{op}[i] && f1_valid) || (sm_{op}[i] && m_valid))'
  needle=f'if(w{op}[i] && available_{op}[i]) begin if(!free_slot[i]) {storage}<={selected};w{op}[i]<=0;end'
  o=rep(o,needle,f'if(w{op}[i] && (available_{op}[i] || {hit})) begin if(!free_slot[i]) {storage}<=({hit} && !{higher}) ? r_data : {selected};w{op}[i]<=0;end')
  needle=f'(wait_{op} && w_valid && tag_{op}==w_tag) ? w_data :';o=rep(o,needle,f'(wait_{op} && r_valid && tag_{op}==r_tag) ? r_data : '+needle)
  needle=f'   else if(wait_{op} && w_valid && tag_{op}==w_tag)';o=rep(o,needle,f'   else if(wait_{op} && r_valid && tag_{op}==r_tag) begin w{op}[wr]<=0;end\n'+needle)
 for name,s in (('nc_core.v',c),('nc_operands.v',o),('nc_memory.v',m)):(out/name).write_text(s)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),accepted_dual_sha256=sha(accepted),trial='loadcapture',scope='Load-return capture-only into existing operand value FFs; current-cycle EX selection/availability unchanged; no raw return-to-EX data/control path; NOT ADOPTED')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',out.name)
if __name__=='__main__':main()
