"""Registered LSU completion buses, parallel to group completion/retirement."""
from pathlib import Path
import json,hashlib,shutil,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 src=ROOT/'simulation/results/load_bp_dual_lsu_ports';out=src.with_name('load_bp_dual_lsu_forward');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_memory.v';s=p.read_text();s=rep(s,' input wire rsp1_valid,output wire rsp1_ready,input wire[31:0] rsp1_data);',' input wire rsp1_valid,output wire rsp1_ready,input wire[31:0] rsp1_data,\n output reg load0_valid,load1_valid,output reg[2:0] load_tag,output reg[31:0] load0_data,load1_data);')
 # Empty FIFO is not a memory stall. This handshake cleanup does not change
 # any accepted input, request, response or retirement cycle.
 s=rep(s,'wire head_allowed=valid && (!input_multiply || mul_ready);','wire head_allowed=!input_multiply || mul_ready;')
 s=rep(s,'wire want_primary=can_start ? (head_allowed && input_primary_memory)','wire want_primary=can_start ? (valid && head_allowed && input_primary_memory)')
 s=rep(s,'wire want_secondary=can_start ? (head_allowed && input_side_memory)','wire want_secondary=can_start ? (valid && head_allowed && input_side_memory)')
 s=rep(s,'(state==IDLE && head_allowed && !input_memory)','(state==IDLE && valid && head_allowed && !input_memory)')
 s=rep(s,' always @(posedge clk) begin',''' always @(posedge clk) begin
  if(primary_response || secondary_response) load_tag<=tag;
  if(primary_response) load0_data<=format_load(rsp_data,held[118:117],held[10:8]);
  if(secondary_response || (primary_response && s_done)) load1_data<=secondary_value;
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin load0_valid<=0;load1_valid<=0;end
  else if(kill) begin load0_valid<=0;load1_valid<=0;end
  else begin
   load0_valid<=primary_response && !rsp_error && kind==4 && held[3] && held[15:11]!=0;
   load1_valid<=(secondary_response || (primary_response && s_done)) && primary_complete && !primary_error &&
                    secondary_complete && side_memory && !side_store && held_side[75:71]!=0;
  end
 end
 always @(posedge clk) begin''');p.write_text(s)
 p=out/'nc_core.v';s=p.read_text();s=rep(s,' wire m_valid,m_lane;', ' wire l0_valid,l1_valid;wire[2:0] l_tag;wire[31:0] l0_data,l1_data;\n wire m_valid,m_lane;')
 s=rep(s,'  .m_valid(m_valid),',"  .l0_valid(l0_valid),.l0_tag({l_tag,1'b0}),.l0_data(l0_data),\n  .l1_valid(l1_valid),.l1_tag({l_tag,1'b1}),.l1_data(l1_data),\n  .m_valid(m_valid),")
 s=rep(s,'  .req1_valid(s_req_valid),','  .load0_valid(l0_valid),.load1_valid(l1_valid),.load_tag(l_tag),.load0_data(l0_data),.load1_data(l1_data),\n  .req1_valid(s_req_valid),');p.write_text(s)
 p=out/'nc_operands.v';s=p.read_text();s=rep(s,' input wire m_valid,input wire[3:0] m_tag,input wire[31:0] m_data,',' input wire m_valid,input wire[3:0] m_tag,input wire[31:0] m_data,\n input wire l0_valid,l1_valid,input wire[3:0] l0_tag,l1_tag,input wire[31:0] l0_data,l1_data,')
 sources=('f','f1','m','l0','l1','w','w1')
 for op in 'abcd':
  val={'a':'va[s]','b':'vb[s]','c':'side[s][135:104]','d':'side[s][103:72]'}[op];wait='w'+op+'[s]';dest={'a':'selected_va','b':'selected_vb','c':'selected_c','d':'selected_d'}[op]
  hits={t:('hit_'+t+op+'[s]' if op in 'ab' else 'h_'+op+'_'+t) for t in ('f','f1','m','w','w1')}
  hits.update({t:'h_'+op+'_'+t for t in ('l0','l1')})
  idx=s.index(f'  assign available_{op}[s]=');s=s[:idx]+''.join(f'  wire h_{op}_{t}={t}_valid && {t}_tag==dep_{op}[s];\n' for t in ('l0','l1'))+s[idx:]
  s=re.sub(r'  assign available_'+op+r'\[s\]=[^;]+;',f'  assign available_{op}[s]=!{wait} || '+' || '.join(hits[t] for t in sources)+';',s)
  for t in ('f','f1','m','w','w1'):s=re.sub(r'  wire use_'+op+'_'+t+r'=[^;]+;\n','',s)
  select='';prev=[]
  for t in sources:
   term=wait+' && '+('!('+' || '.join(prev)+') && ' if prev else '')+hits[t];select+=f'  wire use_{op}_{t}={term};\n';prev.append(hits[t])
  select+=f'  assign {dest}[s]=({{32{{!{wait}}}}} & {val}) |\n   '+' | '.join(f'({{32{{use_{op}_{t}}}}} & {t}_data)' for t in sources)+';'
  s=re.sub(r'  assign '+dest+r'\[s\]=[^;]+;',lambda _:select,s)
  target={'a':'va[wr]','b':'vb[wr]','c':'side[wr][135:104]','d':'side[wr][103:72]'}[op];needle=f'   else if(wait_{op} && w_valid && tag_{op}==w_tag)';assert s.count(needle)==1
  s=s.replace(needle,''.join(f'   else if(wait_{op} && {t}_valid && tag_{op}=={t}_tag) begin {target}<={t}_data;w{op}[wr]<=0;end\n' for t in ('l0','l1'))+needle)
 p.write_text(s)
 for n in ('nc_core.v','nc_memory.v','nc_operands.v'):g['override_sha256']['hardware\\pds\\source\\core\\'+n]=sha(out/n)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope='dual_lsu_forward; dual_lsu_ports plus separately registered formatted load completion buses, available before atomic group retirement; no raw RAM/EX path and no earlier LSU request; accepted baseline unchanged; not adopted')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED dual_lsu_forward')
if __name__=='__main__':main()
