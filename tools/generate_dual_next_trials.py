"""Independent, unadopted IPC/timing trials from the accepted storewrite source."""
from pathlib import Path
import argparse, hashlib, json, shutil, re
ROOT=Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):
 assert s.count(a)==1,(a,s.count(a))
 return s.replace(a,b)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--trial',choices=('probe','mqual','mpre','pairmul','pairbranch','loadwake','wordwake'),required=True);args=ap.parse_args();t=args.trial
 accepted=ROOT/'docs/accepted_dual_baseline.json';d=json.loads(accepted.read_text());assert d['variant']=='dual_boundary_storewrite'
 src=ROOT/d['source_directory'];out=src.with_name('load_bp_dual_boundary_next_'+t);assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 c=(out/'nc_core.v').read_text();o=(out/'nc_operands.v').read_text();m=(out/'nc_memory.v').read_text();mu=(out/'nc_mul_pipeline.v').read_text()
 if t=='mqual':
  mu=rep(mu,'output wire busy,output wire[3:0] next_forward_tag);','output wire busy,output wire[3:0] next_forward_tag,output wire next_forward_valid);')
  mu=rep(mu,' assign next_forward_tag=', ' assign next_forward_valid=rst_n && !clear && (low_done || high_done);\n assign next_forward_tag=')
  c=rep(c,' wire m_valid,m_lane;',' wire m_next_valid;\n wire m_valid,m_lane;')
  c=rep(c,'.next_forward_tag(m_next_tag),','.next_forward_valid(m_next_valid),.next_forward_tag(m_next_tag),')
  c=rep(c,'.next_f_tag(ex_tag),','.next_m_valid(m_next_valid),.next_f_tag(ex_tag),')
  o=rep(o,' input wire[2:0] next_f_tag,',' input wire next_m_valid,\n input wire[2:0] next_f_tag,')
  for op in 'abcd':
   o=rep(o,f'sm_{op}[i]<=((push && wr==i[0]) ? tag_{op} : dep_{op}[i])==next_m_tag;',f'sm_{op}[i]<=(((push && wr==i[0]) ? tag_{op} : dep_{op}[i])==next_m_tag) && next_m_valid;')
   o=rep(o,f'sm_{op}[s] && m_valid',f'sm_{op}[s]')
 if t=='mpre':
  o=rep(o,' output wire occupied);',' output wire occupied,output wire primary_ready);')
  o=rep(o,' assign occupied=count!=0;', ' assign primary_ready=count!=0 && available_a[rd] && available_b[rd];\n assign occupied=count!=0;')
  c=rep(c,' wire ex_credit,ex_valid,',' wire primary_ready;reg primary_mul_started;\n wire ex_credit,ex_valid,')
  c=rep(c,'.occupied(ex_occupied));','.occupied(ex_occupied),.primary_ready(primary_ready));')
  c=rep(c,' wire mul_accept=ex_fire && (ex_multiply || side_multiply);', ''' // Start only the ready primary MUL while the same atomic group holds
 // its younger ALU. No younger group passes and MEM still owns retirement.
 wire primary_mul_early=primary_ready && ex_enable && !primary_mul_started &&
  ex_packet[203:200]==6 && !ex_packet[150] && !ex_packet[1] && !ex_packet[0];
 wire mul_accept=primary_mul_early || (ex_fire && (side_multiply || (ex_multiply && !primary_mul_started)));
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) primary_mul_started<=0;
  else if(redirect || do_trap || ex_fire) primary_mul_started<=0;
  else if(primary_mul_early) primary_mul_started<=1;
 end''')
 if t in ('pairmul','pairbranch'):
  side='!id_insn1[6]' if t=='pairmul' else 'id_insn1[6]'
  c=rep(c,'wire extended_pair=id_pair_flags[9] && id_pair_flags[3] && !id_prediction[31];',f'''wire extended_pair=id_pair_flags[9] && (id_pair_flags[3] ||
  ((id_kind==4 || id_kind==5) && {side})) && !id_prediction[31];''')
  c=c.replace('// A side MUL is admitted only with a legal ordinary ALU primary,','// This trial also admits a side MUL with a primary LSU transaction.\n // Primary faults suppress side retirement; a trap clears speculative MUL state.\n // Original note: A side MUL is admitted only with a legal ordinary ALU primary,')
  if t=='pairmul':
   m=rep(m,' reg posted_response;',' reg posted_response;\n reg saved_response,posted_complete;reg[31:0] saved_load;reg saved_error;')
   m=rep(m,' wire response=memory_pending && sent && rsp_valid && !posted_response;', ' wire raw_response=memory_pending && sent && rsp_valid && !posted_response && !saved_response;\n wire response=raw_response || saved_response;')
   m=rep(m,' wire response_error=response && rsp_error;',' wire response_error=response && (saved_response ? saved_error : rsp_error);')
   m=rep(m,'(!memory_access || response || posted_fire)', '(!memory_access || response || posted_fire || posted_complete)')
   m=rep(m,'(memory_pending && sent && !kill);','(memory_pending && sent && !kill && !saved_response);')
   m=rep(m,'memory_access ? loaded :','memory_access ? (saved_response ? saved_load : loaded) :')
   m=rep(m,' // A detached accepted write is architectural', ''' // Retain a response/posted acceptance if a same-group MUL is still
 // running. Never drop a one-cycle response or repeat an accepted store.
 always @(posedge clk) if(raw_response) begin saved_load<=loaded;saved_error<=rsp_error;end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin saved_response<=0;posted_complete<=0;end
  else if(kill || start || complete) begin saved_response<=0;posted_complete<=0;end
  else begin
   if(raw_response) saved_response<=1;
   if(posted_fire) posted_complete<=1;
  end
 end
 // A detached accepted write is architectural''')
 if t in ('loadwake','wordwake'):
  m=rep(m,'input wire rsp_error);', 'input wire rsp_error,\n output wire return_valid,output wire[2:0] return_tag,output wire[31:0] return_data);')
  m=rep(m,' wire[31:0] completed_result=', ' assign return_valid=wb_valid && !exception && !response_error && kind==4 && wr && rd!=0'+(' && load_word' if t=='wordwake' else '')+';\n assign return_tag=tag;assign return_data='+('rsp_data' if t=='wordwake' else 'loaded')+';\n wire[31:0] completed_result=')
  c=rep(c,' wire m_valid,m_lane;',' wire r_valid;wire[2:0] r_tag;wire[31:0] r_data;\n wire m_valid,m_lane;')
  c=rep(c,'.m_valid(m_valid),.m_tag({m_tag,m_lane}),.m_data(m_data),', '.m_valid(m_valid),.m_tag({m_tag,m_lane}),.m_data(m_data),\n  .r_valid(r_valid),.r_tag({r_tag,1\'b0}),.r_data(r_data),')
  c=rep(c,'.wb_valid(memory_done),.wb_packet(memory_packet),','.return_valid(r_valid),.return_tag(r_tag),.return_data(r_data),\n  .wb_valid(memory_done),.wb_packet(memory_packet),')
  o=rep(o,' input wire m_valid,input wire[3:0] m_tag,input wire[31:0] m_data,',' input wire m_valid,input wire[3:0] m_tag,input wire[31:0] m_data,\n input wire r_valid,input wire[3:0] r_tag,input wire[31:0] r_data,')
  for op in 'abcd':
   wait='w'+op+'[s]';storage={'a':'va[s]','b':'vb[s]','c':'side[s][135:104]','d':'side[s][103:72]'}[op];dest={'a':'selected_va','b':'selected_vb','c':'selected_c','d':'selected_d'}[op]
   hits={p:(f'hit_{p}{op}[s]' if op in 'ab' else f'h_{op}_{p}') for p in ('f','f1','m','w','w1')};hits['r']=f'h_{op}_r'
   marker=f'  assign available_{op}[s]=';i=o.index(marker);o=o[:i]+f'  wire h_{op}_r=r_valid && r_tag==dep_{op}[s];\n'+o[i:]
   o=re.sub(r'  assign available_'+op+r'\[s\]=[^;]+;',f'  assign available_{op}[s]=!{wait} || '+' || '.join(hits[p] for p in ('f','f1','m','r','w','w1'))+';',o)
   for p in ('f','f1','m','w','w1'):o=re.sub(r'  wire use_'+op+'_'+p+r'=[^;]+;\n','',o)
   sels='';prev=[]
   for p in ('f','f1','m','r','w','w1'):
    term=wait+' && '+('!('+' || '.join(prev)+') && ' if prev else '')+hits[p];sels+=f'  wire use_{op}_{p}={term};\n';prev.append(hits[p])
   sels+=f'  assign {dest}[s]=({{32{{!{wait}}}}} & {storage}) |\n   '+' | '.join(f'({{32{{use_{op}_{p}}}}} & {p}_data)' for p in ('f','f1','m','r','w','w1'))+';'
   o=re.sub(r'  assign '+dest+r'\[s\]=[^;]+;',lambda _:sels,o)
   needle=f'(wait_{op} && w_valid && tag_{op}==w_tag) ? w_data :'
   o=rep(o,needle,f'(wait_{op} && r_valid && tag_{op}==r_tag) ? r_data : '+needle)
   needle=f'   else if(wait_{op} && w_valid && tag_{op}==w_tag)'
   o=rep(o,needle,f'   else if(wait_{op} && r_valid && tag_{op}==r_tag) begin w{op}[wr]<=0;end\n'+needle)
 for n,s in (('nc_core.v',c),('nc_operands.v',o),('nc_memory.v',m),('nc_mul_pipeline.v',mu)):(out/n).write_text(s)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),accepted_dual_sha256=sha(accepted),scope='Independent next trial '+t+'; NOT ADOPTED; same PLL80/constraints/images; no seed search',trial=t)
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',out.name)
if __name__=='__main__':main()
