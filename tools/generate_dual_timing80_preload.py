"""Preload only empty operand slots to remove late ID issue from data FF CE."""
from pathlib import Path
import hashlib,json,shutil,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 src=ROOT/'simulation/results/load_bp_dual_boundary_uart';out=src.with_name('load_bp_dual_boundary_preload');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_operands.v';s=p.read_text();pos=' integer i;\n always @(posedge clk) begin'
 declarations=''' // Free physical slots may sample the next operand values before issue.
 // No valid/token/wait state changes before push. Count/rd are registered,
 // so a late decoder/issue signal no longer drives the wide value FF CE.
 wire[1:0] free_slot={count==0 || (count==1 && !rd),count==0 || (count==1 && rd)};
'''
 for op,wait,tag,raw in (('a','wait_a','tag_a','in_packet[135:104]'),('b','wait_b','tag_b','in_packet[103:72]'),('c','wait_c','tag_c','in_side[135:104]'),('d','wait_d','tag_d','in_side[103:72]')):
  expr=raw
  for prod in reversed(('f','f1','m','w','w1')):expr=f'({wait} && {prod}_valid && {tag}=={prod}_tag) ? {prod}_data : '+expr
  declarations+=' wire[31:0] incoming_'+op+'='+expr+';\n'
 s=rep(s,pos,declarations+pos)
 for op,flag,regval,select in (('a','wa','va[i]','selected_va[i]'),('b','wb','vb[i]','selected_vb[i]'),('c','wc','side[i][135:104]','selected_c[i]'),('d','wd','side[i][103:72]','selected_d[i]')):
  s=rep(s,f'if({flag}[i] && available_{op}[i]) begin {regval}<={select};{flag}[i]<=0;end',f'if({flag}[i] && available_{op}[i]) begin if(!free_slot[i]) {regval}<={select};{flag}[i]<=0;end')
 s=rep(s,'  for(i=0;i<2;i=i+1) begin\n','''  for(i=0;i<2;i=i+1) begin
   if(free_slot[i]) begin
    va[i]<=incoming_a;vb[i]<=incoming_b;
    side[i][135:104]<=incoming_c;side[i][103:72]<=incoming_d;
   end
''')
 s=rep(s,'side[wr]<=in_side;payload[wr]<=in_packet;', 'side[wr][223:136]<=in_side[223:136];side[wr][71:0]<=in_side[71:0];payload[wr]<=in_packet;')
 s=rep(s,'wa[wr]<=wait_a;wb[wr]<=wait_b;va[wr]<=in_packet[135:104];vb[wr]<=in_packet[103:72];','wa[wr]<=wait_a;wb[wr]<=wait_b;')
 for dest in ('va[wr]','vb[wr]','side[wr][135:104]','side[wr][103:72]'):
  pattern=re.escape(dest)+r'<=\w+_data;';s,n=re.subn(pattern,'',s);assert n==5,(dest,n)
 p.write_text(s)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope='dual_boundary_preload; UART80 integrated, empty operand slot value preload removes ID issue from value CE; occupied values, credit, forwarding priority and architectural schedule unchanged; research not adopted')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED dual_boundary_preload')
if __name__=='__main__':main()
