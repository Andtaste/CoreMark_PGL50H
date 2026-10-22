"""Joint sliding supply, compact four-source capture, and branch/MUL admission trials."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_joint_ready','dual_joint_wait','dual_joint_branch'),required=True);a=ap.parse_args()
 src=ROOT/'simulation/results/load_bp_dual_types_slide_admit';out=src.with_name('load_bp_'+a.variant);assert not out.exists(),out;out.mkdir()
 g=json.loads((src/'generation.json').read_text());parent=ROOT/'simulation/results/load_bp_dual_fwd_share'
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h,n;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 s=(out/'nc_core.v').read_text()
 s=rep(s,'reg dep_a,dep_b,second_dep;reg[3:0] tag_a,tag_b;', 'reg dep_a,dep_b,dep_c,dep_d,second_dep;reg[3:0] tag_a,tag_b,tag_c,tag_d;\n reg[7:0] match_c,match_c1,match_d,match_d1;reg[15:0] producers_c,producers_d;')
 s=rep(s,'dep_a=0;dep_b=0;tag_a=0;tag_b=0;', 'dep_a=0;dep_b=0;dep_c=0;dep_d=0;tag_a=0;tag_b=0;tag_c=0;tag_d=0;\n  match_c=0;match_c1=0;match_d=0;match_d1=0;')
 old='''    if((id_pair_flags[5] && rs1_1!=0 && (destination[n]==rs1_1 || destination1[n]==rs1_1)) ||
       (id_pair_flags[6] && rs2_1!=0 && (destination[n]==rs2_1 || destination1[n]==rs2_1))) second_dep=1;'''
 s=rep(s,old,'''    match_c[n]=destination[n]!=0 && destination[n]==rs1_1;
    match_d[n]=destination[n]!=0 && destination[n]==rs2_1;
    match_c1[n]=destination1[n]!=0 && destination1[n]==rs1_1;
    match_d1[n]=destination1[n]!=0 && destination1[n]==rs2_1;''')
 s=rep(s,'producers_b[2*n]=match_b[n];producers_b[2*n+1]=match_b1[n];', 'producers_b[2*n]=match_b[n];producers_b[2*n+1]=match_b1[n];\n   producers_c[2*n]=match_c[n];producers_c[2*n+1]=match_c1[n];\n   producers_d[2*n]=match_d[n];producers_d[2*n+1]=match_d1[n];')
 s=rep(s,'dep_a=use1 && |(match_a|match_a1);dep_b=use2 && |(match_b|match_b1);', '''dep_a=use1 && |(match_a|match_a1);dep_b=use2 && |(match_b|match_b1);
  tag_c=|(producers_c & below_tail16) ? newest4(producers_c & below_tail16) : newest4(producers_c);
  tag_d=|(producers_d & below_tail16) ? newest4(producers_d & below_tail16) : newest4(producers_d);
  dep_c=id_pair_flags[5] && |(match_c|match_c1);dep_d=id_pair_flags[6] && |(match_d|match_d1);''')
 if a.variant=='dual_joint_ready':
  terms=[]
  for op in 'cd':
   hits=[f'(f_valid && tag_{op}=={{f_tag,1\'b0}})',f'(f1_valid && tag_{op}=={{f1_tag,1\'b1}})',f'(m_valid && tag_{op}=={{m_tag,m_lane}})',f'(commit && w_wr && w_rd!=0 && tag_{op}=={{w_tag,1\'b0}})',f'(commit1 && w1_rd!=0 && tag_{op}=={{w_tag,1\'b1}})']
   terms.append(f'(dep_{op} && !('+ ' || '.join(hits)+'))')
  s=rep(s,'  dep_c=id_pair_flags[5] && |(match_c|match_c1);dep_d=id_pair_flags[6] && |(match_d|match_d1);','  dep_c=id_pair_flags[5] && |(match_c|match_c1);dep_d=id_pair_flags[6] && |(match_d|match_d1);\n  second_dep='+ ' || '.join(terms)+';')
 s=rep(s,'.wait_a(dep_a),.wait_b(dep_b),', '.wait_c(pair_candidate && dep_c),.wait_d(pair_candidate && dep_d),.tag_c(tag_c),.tag_d(tag_d),\n  .wait_a(dep_a),.wait_b(dep_b),')
 if a.variant=='dual_joint_branch':
  # The normal side ALU is annulled when primary branch prediction is wrong.
  # Primary predicted-taken branches are deliberately not paired; one branch/group.
  f=(out/'nc_fetch.v').read_text()
  f=rep(f,'begin pack_flags={|parts[7:3],','begin pack_flags={|parts[8:3],')
  (out/'nc_fetch.v').write_text(f)
 (out/'nc_core.v').write_text(s)
 # Reuse the existing side packet's 64 operand bits as capture storage. No
 # extra C/D value array, lookahead-tag protocol, or duplicated payload bank.
 s=(parent/'nc_operands.v').read_text()
 s=rep(s,'reg[223:0] side[0:1];assign out_side=side[rd];','reg[223:0] side[0:1];\n reg[3:0] dep_c[0:1],dep_d[0:1];reg[1:0] wc,wd;\n input wire wait_c,wait_d;input wire[3:0] tag_c,tag_d;\n wire[1:0] available_c,available_d;wire[31:0] selected_c[0:1],selected_d[0:1];\n assign out_side={side[rd][223:136],selected_c[rd],selected_d[rd],side[rd][71:0]};')
 # Ports must be declared in the ANSI list, not after it.
 s=s.replace(' input wire wait_c,wait_d;input wire[3:0] tag_c,tag_d;\n','')
 s=rep(s,' input wire wait_a,wait_b,input wire[3:0] tag_a,tag_b,',' input wire wait_a,wait_b,input wire[3:0] tag_a,tag_b,\n input wire wait_c,wait_d,input wire[3:0] tag_c,tag_d,')
 block=''
 for op,lo in [('c',104),('d',72)]:
  hits=[]
  for source in ['f','f1','m','w','w1']:
   name=f'h_{op}_{source}';block+=f'  wire {name}={source}_valid && {source}_tag==dep_{op}[s];\n';hits.append(name)
  block+=f'  assign available_{op}[s]=!w{op}[s] || '+ ' || '.join(hits)+';\n'
  expr=[f'({{32{{!w{op}[s]}}}} & side[s][{lo+31}:{lo}])']
  for i,source in enumerate(['f','f1','m','w','w1']):
   mask=f'w{op}[s] && '+('!('+' || '.join(hits[:i])+') && ' if i else '')+hits[i]
   block+=f'  wire use_{op}_{source}={mask};\n';expr.append(f'({{32{{use_{op}_{source}}}}} & {source}_data)')
  block+=f'  assign selected_{op}[s]='+' |\n   '.join(expr)+';\n'
 s=rep(s,' end endgenerate',block+' end endgenerate')
 s=rep(s,'available_a[rd] && available_b[rd];','available_a[rd] && available_b[rd] && available_c[rd] && available_d[rd];')
 s=rep(s,'  end\n  if(push) begin','''   if(wc[i] && available_c[i]) begin side[i][135:104]<=selected_c[i];wc[i]<=0;end
   if(wd[i] && available_d[i]) begin side[i][103:72]<=selected_d[i];wd[i]<=0;end
  end
  if(push) begin''')
 insertion='''   dep_c[wr]<=tag_c;dep_d[wr]<=tag_d;wc[wr]<=wait_c;wd[wr]<=wait_d;
'''
 for op,lo in [('c',104),('d',72)]:
  for i,source in enumerate(['f','f1','m','w','w1']):
   insertion+=('   if' if i==0 else '   else if')+f'(wait_{op} && {source}_valid && tag_{op}=={source}_tag) begin side[wr][{lo+31}:{lo}]<={source}_data;w{op}[wr]<=0;end\n'
 s=rep(s,'   predictions[wr]<=in_prediction;',insertion+'   predictions[wr]<=in_prediction;')
 (out/'nc_operands.v').write_text(s)
 for name in ['nc_core.v','nc_operands.v','nc_fetch.v']:g['override_sha256']['hardware\\pds\\source\\core\\'+name]=sha(out/name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope=a.variant+'; isolated re-design from accepted architecture using compact lower-word sliding cache and four-source capture in existing side packet; original 249x4 EXMEM and 1LSU/1MUL; no adoption',forward_policy='current_registered_broadcast_only' if 'ready' in a.variant else 'tagged_older_results_capture_and_wait')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',a.variant)

if __name__=='__main__':main()
