"""Integrated old-core lessons, in isolated and immutable research candidates."""
from pathlib import Path
import argparse,hashlib,json,shutil,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,a,b):
 assert s.count(a)==1,(a,s.count(a))
 return s.replace(a,b)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_legacy_fifo','dual_legacy_return','dual_legacy_split'),required=True);a=ap.parse_args()
 parent=ROOT/'simulation/results/load_bp_dual_joint_fix';out=parent.with_name('load_bp_'+a.variant);assert not out.exists();out.mkdir()
 g=json.loads((parent/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=parent/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(parent/'ipcore',out/'ipcore');shutil.copyfile(parent/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 # Preserve extended branch/MUL predecode while replacing group/peek state
 # with eight individual words in two parity banks. RAM reads use rd only.
 f=(ROOT/'simulation/research/dual_native/nc_fetch.v').read_text();j=(parent/'nc_fetch.v').read_text()
 lo=j.index(' function[8:0] classify_parts');hi=j.index(' reg[17:0] flags',lo)
 start=f.index(' function[7:0] classify_parts');end=f.index(' // Eight individual instructions',start)
 f=f[:start]+j[lo:hi]+f[end:]
 for x,y in [('[105:0]','[106:0]'),('[73:0] even_meta','[74:0] even_meta'),('[105:74]','[106:75]'),('[73:42]','[74:43]'),('[41:34]','[42:34]'),('[105:32]','[106:32]'),("106'b0","107'b0")]:f=f.replace(x,y)
 f=once(f,'assign pair_flags={pack_flags(head_1[42:34]),pack_flags(head_0[42:34])};','assign pair_flags={head_1[42],pack_flags(head_1[42:34])[3:0],pack_flags(head_0[42:34])};')
 # Verilog cannot slice a function invocation portably.
 f=f.replace(' assign pair_flags={head_1[42],pack_flags(head_1[42:34])[3:0],pack_flags(head_0[42:34])};',' wire[4:0] side_flags=pack_flags(head_1[42:34]);\n assign pair_flags={head_1[42],side_flags[3:0],pack_flags(head_0[42:34])};')
 f=f.replace('// Isolated dual-width frontend: four registered groups, at most eight words.','// Eight-word sliding instruction FIFO, two parity banks and two cached heads.')
 (out/'nc_fetch.v').write_text(f)
 if a.variant!='dual_legacy_fifo':
  c=(out/'nc_core.v').read_text();m=(out/'nc_memory.v').read_text();o=(out/'nc_operands.v').read_text()
  # Synchronous RAM output can feed a consumer on the WB capture edge.
  # Request generation and FIFO credit are unchanged; faults never broadcast.
  m=once(m,' input wire rsp_valid,output wire rsp_ready,input wire[31:0] rsp_data,input wire rsp_error);',' input wire rsp_valid,output wire rsp_ready,input wire[31:0] rsp_data,input wire rsp_error,\n output wire return_valid,output wire[2:0] return_tag,output wire[31:0] return_data);')
  m=once(m,' wire memory_pending=state==MEMORY,buffered=state==BUFFERED;',' wire memory_pending=state==MEMORY,buffered=state==BUFFERED;\n assign return_valid=memory_pending && rsp_valid && !rsp_error && !kill && !exception && kind==4 && wr && rd!=0;\n assign return_tag=tag;assign return_data=loaded;')
  m=m.replace('// RAM return/formatting terminates at the separate WB data register. There\n// is no raw-RAM -> EX bypass and no extra response-copy cycle in MEM.','// Synchronous RAM return/formatting also broadcasts to dependent operands.\n// Requests still originate at the registered FIFO boundary.')
  c=once(c,' wire m_valid,m_lane;',' wire r_valid;wire[2:0] r_tag;wire[31:0] r_data;\n wire m_valid,m_lane;')
  c=once(c,'  .m_valid(m_valid),.m_tag({m_tag,m_lane}),.m_data(m_data),','  .m_valid(m_valid),.m_tag({m_tag,m_lane}),.m_data(m_data),\n  .r_valid(r_valid),.r_tag({r_tag,1\'b0}),.r_data(r_data),')
  c=once(c,'  .wb_valid(memory_done),.wb_packet(memory_packet),','  .return_valid(r_valid),.return_tag(r_tag),.return_data(r_data),\n  .wb_valid(memory_done),.wb_packet(memory_packet),')
  o=once(o,' input wire m_valid,input wire[3:0] m_tag,input wire[31:0] m_data,',' input wire m_valid,input wire[3:0] m_tag,input wire[31:0] m_data,\n input wire r_valid,input wire[3:0] r_tag,input wire[31:0] r_data,')
  # Rebuild operand selections from an explicit priority list. Preserve packet
  # storage, tags, occupancy, and capture semantics; add exactly one source.
  for op in 'abcd':
   val={'a':'va[s]','b':'vb[s]','c':'side[s][135:104]','d':'side[s][103:72]'}[op]
   wait='w'+op+'[s]';dest={'a':'selected_va','b':'selected_vb','c':'selected_c','d':'selected_d'}[op]
   if op in 'ab':
    hits={'f':'hit_f'+op+'[s]','f1':'hit_f1'+op+'[s]','m':'hit_m'+op+'[s]','w':'hit_w'+op+'[s]','w1':'hit_w1'+op+'[s]'}
   else:hits={p:'h_'+op+'_'+p for p in ('f','f1','m','w','w1')}
   hits['r']='h_'+op+'_r'
   marker=f'  assign available_{op}[s]='
   idx=o.index(marker);o=o[:idx]+f'  wire h_{op}_r=r_valid && r_tag==dep_{op}[s];\n'+o[idx:]
   o=re.sub(r'  assign available_'+op+r'\[s\]=[^;]+;',f'  assign available_{op}[s]=!{wait} || '+' || '.join(hits[p] for p in ('f','f1','m','r','w','w1'))+';',o)
   for p in ('f','f1','m','w','w1'):
    o=re.sub(r'  wire use_'+op+'_'+p+r'=[^;]+;\n','',o)
   select='';prev=[]
   for p in ('f','f1','m','r','w','w1'):
    term=wait+' && '+('!('+' || '.join(prev)+') && ' if prev else '')+hits[p]
    select+=f'  wire use_{op}_{p}={term};\n';prev.append(hits[p])
   select+=f'  assign {dest}[s]=({{32{{!{wait}}}}} & {val}) |\n   '+' | '.join(f'({{32{{use_{op}_{p}}}}} & {p}_data)' for p in ('f','f1','m','r','w','w1'))+';'
   o=re.sub(r'  assign '+dest+r'\[s\]=[^;]+;',lambda _:select,o)
   # The input slot may be inserted during a response. Capture the value on
   # that edge even if it will have disappeared by the next cycle.
   target={'a':'va[wr]','b':'vb[wr]','c':'side[wr][135:104]','d':'side[wr][103:72]'}[op]
   needle=f'   else if(wait_{op} && w_valid && tag_{op}==w_tag)'
   assert o.count(needle)==1
   o=o.replace(needle,f'   else if(wait_{op} && r_valid && tag_{op}==r_tag) begin {target}<=r_data;w{op}[wr]<=0;end\n'+needle)
  if a.variant=='dual_legacy_split':
   c=once(c,' reg barrier;reg[7:0] live;',' reg[7:0] slow_main,slow_side;\n reg barrier;reg[7:0] live;')
   # Reject any older slow producer before tag encoding. This intentionally
   # conservative policy avoids encoder -> dynamic class RAM -> IF feedback.
   needle='    match_d1[n]=destination1[n]!=0 && destination1[n]==rs2_1;'
   c=once(c,needle,needle+'\n    if((slow_main[n] && ((id_pair_flags[5] && match_c[n]) || (id_pair_flags[6] && match_d[n]))) ||\n       (slow_side[n] && ((id_pair_flags[5] && match_c1[n]) || (id_pair_flags[6] && match_d1[n])))) second_dep=1;')
   c=once(c,' wire ex_credit,ex_valid,',' always @(posedge clk) if(issue) begin slow_main[tail]<=id_kind==4 || id_kind==6;slow_side[tail]<=id_side_kind==6;end\n wire ex_credit,ex_valid,')
  (out/'nc_core.v').write_text(c);(out/'nc_memory.v').write_text(m);(out/'nc_operands.v').write_text(o)
 for p in out.glob('*.v'):
  key='hardware\\pds\\source\\core\\'+p.name
  if key in g['override_sha256']:g['override_sha256'][key]=sha(p)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(parent/'generation.json'),scope=a.variant+'; individual word FIFO8, joint branch/MUL and four-source bypass; return adds synchronous load-output bypass; split additionally rejects older slow producer dependencies before tag encoding; one LSU, no independent retirement; not adopted')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',a.variant)
if __name__=='__main__':main()
