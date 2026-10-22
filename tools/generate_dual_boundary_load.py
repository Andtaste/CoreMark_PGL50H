"""Refine measured early-request critical paths: loads only and prepared tag matches."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 src=ROOT/'simulation/results/load_bp_dual_boundary_early';out=src.with_name('load_bp_dual_boundary_load');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_memory.v';s=p.read_text();s=rep(s,'&& input_memory && input_local;','&& input_memory && packet[7:4]==4 && input_local;')
 s=rep(s,"assign req_data=request_data << {request_address[1:0],3'b0};", "assign req_data=store_data << {address[1:0],3'b0};")
 s=rep(s,"assign req_mask=request_f3[1:0]==0 ? (4'b1<<request_address[1:0]) : request_f3[1:0]==1 ? (4'b11<<request_address[1:0]) : 4'b1111;", "assign req_mask=f3[1:0]==0 ? (4'b1<<address[1:0]) : f3[1:0]==1 ? (4'b11<<address[1:0]) : 4'b1111;")
 s=rep(s,'assign req_write=use_input ? packet[7:4]==5 : kind==5;','assign req_write=old_request && kind==5;');p.write_text(s)
 reg=ROOT/'simulation/results/load_bp_dual_joint_reg/nc_operands.v';shutil.copyfile(reg,out/'nc_operands.v')
 p=out/'nc_mul_pipeline.v';s=p.read_text();s=rep(s,' output wire busy);',' output wire busy,output wire[3:0] next_forward_tag);');s=rep(s,' wire low_done=v1 && op1==0,high_done=v2 && op2!=0;',' wire low_done=v1 && op1==0,high_done=v2 && op2!=0;\n assign next_forward_tag=low_done ? {tag1,lane1} : {tag2,lane2};');p.write_text(s)
 p=out/'nc_core.v';s=p.read_text();s=rep(s,'wire m_valid,m_lane;wire[2:0] m_tag;','wire m_valid,m_lane;wire[2:0] m_tag;wire[3:0] m_next_tag;wire[2:0] future_w_tag;');s=rep(s,'.query_tag(mul_query_tag),.consume(mul_consume)', '.next_forward_tag(m_next_tag),.query_tag(mul_query_tag),.consume(mul_consume)');s=rep(s,'wire[276:0] execute_packet;wire[279:0] mem_packet,memory_packet;','wire[276:0] execute_packet;wire[279:0] mem_packet,memory_packet;\n assign future_w_tag=memory_packet[279:277];');s=rep(s,'.wait_c(pair_candidate && dep_c),', '.next_f_tag(ex_tag),.next_w_tag(future_w_tag),.next_m_tag(m_next_tag),\n  .wait_c(pair_candidate && dep_c),');p.write_text(s)
 for name in ('nc_core.v','nc_memory.v','nc_operands.v','nc_mul_pipeline.v'):g['override_sha256']['hardware\\pds\\source\\core\\'+name]=sha(out/name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),reused_operand_sha256=sha(reg),scope='dual_boundary_load; early local loads only, stores remain registered; precompute five producer identity matches without a data stage; no raw load return/no secondary LSU; not adopted')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED dual_boundary_load')
if __name__=='__main__':main()
