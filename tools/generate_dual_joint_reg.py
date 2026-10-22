"""Register producer-identity matches before EX while retaining compact side storage."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 src=ROOT/'simulation/results/load_bp_dual_joint_fix';out=src.with_name('load_bp_dual_joint_reg');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_mul_pipeline.v';s=p.read_text();s=rep(s,' output wire busy);',' output wire busy,output wire[3:0] next_forward_tag);');s=rep(s,' wire low_done=v1 && op1==0,high_done=v2 && op2!=0;',' wire low_done=v1 && op1==0,high_done=v2 && op2!=0;\n assign next_forward_tag=low_done ? {tag1,lane1} : {tag2,lane2};');p.write_text(s)
 p=out/'nc_core.v';s=p.read_text();s=rep(s,'wire m_valid,m_lane;wire[2:0] m_tag;','wire m_valid,m_lane;wire[2:0] m_tag;wire[3:0] m_next_tag;wire[2:0] future_w_tag;')
 s=rep(s,'.query_tag(mul_query_tag),.consume(mul_consume)', '.next_forward_tag(m_next_tag),.query_tag(mul_query_tag),.consume(mul_consume)')
 s=rep(s,'wire[276:0] execute_packet;wire[279:0] mem_packet,memory_packet;','wire[276:0] execute_packet;wire[279:0] mem_packet,memory_packet;\n assign future_w_tag=memory_packet[279:277];')
 s=rep(s,'.wait_c(pair_candidate && dep_c),', '.next_f_tag(ex_tag),.next_w_tag(future_w_tag),.next_m_tag(m_next_tag),\n  .wait_c(pair_candidate && dep_c),');p.write_text(s)
 p=out/'nc_operands.v';s=p.read_text();s=rep(s,' input wire wait_c,wait_d,input wire[3:0] tag_c,tag_d,', ' input wire wait_c,wait_d,input wire[3:0] tag_c,tag_d,\n input wire[2:0] next_f_tag,next_w_tag,input wire[3:0] next_m_tag,')
 declarations='';block=''
 for op in 'abcd':
  for producer in ['f','f1','m','w','w1']:
   name=f's{producer}_{op}';declarations+=f' reg[1:0] {name};\n'
   identity="{next_f_tag,1'b0}" if producer=='f' else "{next_f_tag,1'b1}" if producer=='f1' else 'next_m_tag' if producer=='m' else "{next_w_tag,1'b0}" if producer=='w' else "{next_w_tag,1'b1}"
   block+=f'   {name}[i]<=((push && wr==i[0]) ? tag_{op} : dep_{op}[i])=={identity};\n'
   old=f'{producer}_valid && {producer}_tag==dep_{op}[s]';assert s.count(old)==1,(op,producer,s.count(old));s=s.replace(old,f'{name}[s] && {producer}_valid')
 s=rep(s,' genvar s;', declarations+' genvar s;')
 s=rep(s,'  for(i=0;i<2;i=i+1) begin', '  for(i=0;i<2;i=i+1) begin\n'+block)
 p.write_text(s)
 for name in ['nc_core.v','nc_operands.v','nc_mul_pipeline.v']:g['override_sha256']['hardware\\pds\\source\\core\\'+name]=sha(out/name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope='dual_joint_reg; joint fixed branch/slide with compact side capture; compare next registered F/M/W producer identities before EX; actual valid/data only from registered broadcasts, no ready prediction; no adoption')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED dual_joint_reg')
if __name__=='__main__':main()
