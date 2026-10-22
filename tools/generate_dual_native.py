"""Native instruction FIFO and lookahead-registered tagged forwarding trials."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_native_fifo','dual_native_select','dual_native_forward','dual_native_both'),required=True);a=ap.parse_args()
 src=ROOT/'simulation/results/load_bp_dual_fwd_share';out=src.with_name('load_bp_'+a.variant);out.mkdir(exist_ok=True)
 meta=json.loads((src/'generation.json').read_text())
 for n,h in meta['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h,n;shutil.copyfile(p,out/p.name)
 for n,h in meta['ip_sha256'].items():assert sha(ROOT/n)==h,n
 shutil.copytree(src/'ipcore',out/'ipcore',dirs_exist_ok=True);shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 changed=[]
 if a.variant in ('dual_native_fifo','dual_native_both'):
  shutil.copyfile(ROOT/'simulation/research/dual_native/nc_fetch.v',out/'nc_fetch.v');changed.append('nc_fetch.v')
 if a.variant!='dual_native_fifo':
  shutil.copyfile(ROOT/'simulation/research/dual_native/nc_operands.v',out/'nc_operands.v');changed.append('nc_operands.v')
  s=(ROOT/'hardware/pds/source/core/nc_mul_pipeline.v').read_text()
  s=s.replace(' output wire busy);',' output wire busy,output wire[2:0] next_forward_tag);')
  s=s.replace(' wire low_done=v1 && op1==0,high_done=v2 && op2!=0;',' wire low_done=v1 && op1==0,high_done=v2 && op2!=0;\n assign next_forward_tag=low_done ? tag1 : tag2;')
  (out/'nc_mul_pipeline.v').write_text(s);changed.append('nc_mul_pipeline.v')
  s=(out/'nc_core.v').read_text();s=s.replace('wire m_valid;wire[2:0] m_tag;', 'wire m_valid;wire[2:0] m_tag,m_next_tag,future_w_tag;')
  s=s.replace('.query_tag(mul_query_tag),.consume(mul_consume)', '.next_forward_tag(m_next_tag),.query_tag(mul_query_tag),.consume(mul_consume)')
  s=s.replace('wire[276:0] execute_packet;wire[279:0] mem_packet,memory_packet;', 'wire[276:0] execute_packet;wire[279:0] mem_packet,memory_packet;\n assign future_w_tag=memory_packet[279:277];')
  if a.variant=='dual_native_select':extra=".wait_c(1'b0),.wait_d(1'b0),.tag_c(4'b0),.tag_d(4'b0),"
  else:
   s=s.replace(' reg barrier;reg[7:0] live;', ' reg[7:0] slow_main;\n reg barrier;reg[7:0] live;')
   s=s.replace('reg dep_a,dep_b,second_dep;reg[3:0] tag_a,tag_b;', 'reg dep_a,dep_b,dep_c,dep_d,second_dep;reg[3:0] tag_a,tag_b,tag_c,tag_d;\n reg[7:0] match_c,match_c1,match_d,match_d1;reg[15:0] producers_c,producers_d;')
   s=s.replace('dep_a=0;dep_b=0;tag_a=0;tag_b=0;', 'dep_a=0;dep_b=0;dep_c=0;dep_d=0;tag_a=0;tag_b=0;tag_c=0;tag_d=0;\n  match_c=0;match_c1=0;match_d=0;match_d1=0;')
   old='''    if((id_pair_flags[5] && rs1_1!=0 && (destination[n]==rs1_1 || destination1[n]==rs1_1)) ||
       (id_pair_flags[6] && rs2_1!=0 && (destination[n]==rs2_1 || destination1[n]==rs2_1))) second_dep=1;'''
   new='''    match_c[n]=destination[n]!=0 && destination[n]==rs1_1;
    match_d[n]=destination[n]!=0 && destination[n]==rs2_1;
    match_c1[n]=destination1[n]!=0 && destination1[n]==rs1_1;
    match_d1[n]=destination1[n]!=0 && destination1[n]==rs2_1;
    // Unretired load/MUL/DIV consumers still split. Older ordinary ALU
    // writers may be followed through the registered selector boundary.
    if(slow_main[n] && ((id_pair_flags[5] && match_c[n]) || (id_pair_flags[6] && match_d[n]))) second_dep=1;'''
   assert old in s;s=s.replace(old,new)
   s=s.replace('producers_b[2*n]=match_b[n];producers_b[2*n+1]=match_b1[n];', 'producers_b[2*n]=match_b[n];producers_b[2*n+1]=match_b1[n];\n   producers_c[2*n]=match_c[n];producers_c[2*n+1]=match_c1[n];\n   producers_d[2*n]=match_d[n];producers_d[2*n+1]=match_d1[n];')
   s=s.replace('dep_a=use1 && |(match_a|match_a1);dep_b=use2 && |(match_b|match_b1);', 'dep_a=use1 && |(match_a|match_a1);dep_b=use2 && |(match_b|match_b1);\n  tag_c=|(producers_c & below_tail16) ? newest4(producers_c & below_tail16) : newest4(producers_c);\n  tag_d=|(producers_d & below_tail16) ? newest4(producers_d & below_tail16) : newest4(producers_d);\n  dep_c=id_pair_flags[5] && |(match_c|match_c1);dep_d=id_pair_flags[6] && |(match_d|match_d1);')
   # Only a live entry observes this class, so no reset array is needed.
   s=s.replace(' wire ex_credit,ex_valid,', ' always @(posedge clk) if(issue) slow_main[tail]<=id_kind==4 || id_kind==6;\n wire ex_credit,ex_valid,')
   extra='.wait_c(pair_candidate && dep_c),.wait_d(pair_candidate && dep_d),.tag_c(tag_c),.tag_d(tag_d),'
  s=s.replace('.wait_a(dep_a),.wait_b(dep_b),', extra+'\n  .next_f_tag(ex_tag),.next_w_tag(future_w_tag),.next_m_tag(m_next_tag),\n  .wait_a(dep_a),.wait_b(dep_b),')
  (out/'nc_core.v').write_text(s);changed.append('nc_core.v')
 for file in changed:meta['override_sha256']['hardware\\pds\\source\\core\\'+file]=sha(out/file)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 meta['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 meta.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope=a.variant+'; accepted dual_fwd_share parent; instruction FIFO8 and/or registered prediction of tagged F/M/W broadcasts; no EX-to-RAM bypass, no second LSU',
  canonical_sha256={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'simulation/research/dual_native').glob('*.v')})
 (out/'generation.json').write_text(json.dumps(meta,indent=2)+'\n');print('GENERATED',a.variant)
if __name__=='__main__':main()
