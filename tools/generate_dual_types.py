"""Conditional-branch/shared-MUL side pairing, retaining accepted queue/forwarding."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_types_branch','dual_types_mul','dual_types_both'),required=True);a=ap.parse_args()
 branch=a.variant!='dual_types_mul';mul=a.variant!='dual_types_branch'
 src=ROOT/'simulation/results/load_bp_dual_fwd_share';out=src.with_name('load_bp_'+a.variant);out.mkdir(exist_ok=True)
 g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h,n;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore',dirs_exist_ok=True);shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 s=(out/'nc_fetch.v').read_text()
 s=s.replace('function[7:0] classify_parts','function[8:0] classify_parts').replace('input[7:0] parts','input[8:0] parts')
 s=s.replace('classify_parts={multiply_op,memory_op',f"classify_parts={{(({int(branch)} && op==7'h63 && f3!=2 && f3!=3 && !insn[8]) || ({int(mul)} && multiply_op)),multiply_op,memory_op")
 s=s.replace("op!=7'h23,reg_op,imm_op || reg_op", "op!=7'h23 && op!=7'h63,reg_op || op==7'h63,imm_op || reg_op || op==7'h63")
 s=s.replace('reg[15:0] flags','reg[17:0] flags').replace('reg[15:0] head_parts;assign pair_flags={pack_flags(head_parts[15:8]),pack_flags(head_parts[7:0])};',
  'reg[17:0] head_parts;wire[4:0] second_flags=pack_flags(head_parts[17:9]);\n assign pair_flags={head_parts[17],second_flags[3:0],pack_flags(head_parts[8:0])};')
 s=s.replace('wire[15:0] incoming_flags','wire[17:0] incoming_flags').replace("{8'b0,classify_parts", "{9'b0,classify_parts").replace("{8'b0,head_parts[15:8]}","{9'b0,head_parts[17:9]}").replace("16'b0","18'b0")
 s=s.replace(' // Simulation observability only;', ' // Simulation observability only;')
 idx=s.index(' reg[17:0] flags')
 s=s[:idx]+''' function[4:0] classify_side;
  input[31:0] insn;reg[8:0] p;reg[4:0] f;
  begin p=classify_parts(insn);f=pack_flags(p);classify_side={p[8],f[3:0]};end
 endfunction
'''+s[idx:]
 (out/'nc_fetch.v').write_text(s)
 s=(out/'nc_core.v').read_text()
 s=rep(s,'wire commit1=commit && w_side[64];','''wire commit1=commit && w_side[64];
 wire w1_branch=w1_insn[6:0]==7'h63;
 wire w1_wr=!w1_branch;''')
 s=rep(s,'wire[4:0] w1_rd=w1_insn[11:7];',"wire[4:0] w1_rd=w1_branch ? 5'b0 : w1_insn[11:7];")
 s=s.replace('.we1(commit1)', '.we1(commit1 && w1_wr)')
 s=rep(s,'wire pair_candidate=id_second', '''wire extended_pair=id_pair_flags[9] && id_pair_flags[3] && !id_prediction[31];
 wire pair_candidate=id_second''')
 s=rep(s,'!id_prediction[30] && !id_prediction1[31] && id_pair_flags[8] &&',
  "!id_prediction[30] && ((id_pair_flags[8] && !id_prediction1[31]) || (extended_pair && (id1_kind==1 || !id_prediction1[31]))) &&")
 # Do not interpret B-immediate bits as a destination register.
 s=rep(s,'!(id_pair_flags[2] && rd!=0 && rd==rd1);','!(id_pair_flags[2] && id1_wr && rd!=0 && rd==rd1);')
 side_kind="(id_insn1[6] ? 4'd1 : 4'd6)" if branch and mul else "4'd1" if branch else "4'd6"
 s=rep(s,'wire[223:0] ex_side;', 'wire[223:0] ex_side;\n wire[3:0] id_side_kind=extended_pair ? '+side_kind+" : 4'd0;")
 s=rep(s,"id_side={pair_candidate,id1_control,4'b0,id_pc+32'd4,id_insn1,c,d,id1_imm,32'b0,rd1,id1_wr,2'b0}",
  "id_side={pair_candidate,id1_control,id_side_kind,id_pc+32'd4,id_insn1,c,d,id1_imm,id_prediction1,rd1,id1_wr,2'b0}")
 s=rep(s,'nc_execute execute1(', 'nc_execute #(.ENABLE_DIV(0)) execute1(')
 execute=(ROOT/'hardware/pds/source/core/nc_execute.v').read_text()
 execute=rep(execute,'module nc_execute(', 'module nc_execute #(parameter ENABLE_DIV=1)(')
 start=execute.index(' nc_divide md(');end=execute.index(' always @* begin',start)
 execute=execute[:start]+" generate if(ENABLE_DIV) begin:divider\n"+execute[start:end]+" end else begin:no_divider\n assign md_done=1'b1;assign md_result=32'b0;\n end endgenerate\n"+execute[end:]
 (out/'nc_execute.v').write_text(execute)
 s=rep(s,'wire[276:0] secondary_result;', '''wire[276:0] secondary_result;wire side_wrong,side_taken;wire[31:0] side_target;
 wire side_branch=ex_side[223] && ex_side[203:200]==1;
 wire side_multiply=ex_side[223] && ex_side[203:200]==6;
 wire resolved_branch=ex_branch || side_branch;
 wire[31:0] resolved_prediction=side_branch ? ex_side[39:8] : ex_prediction;
 wire resolved_taken=side_branch ? side_taken : execute_taken;
 wire[31:0] resolved_target=side_branch ? side_target : execute_target;''')
 s=rep(s,".redirect_needed(),.redirect_target(),.prediction(32'b0),.prediction_wrong(),.branch_taken(),",
  '.redirect_needed(),.redirect_target(side_target),.prediction(ex_side[39:8]),.prediction_wrong(side_wrong),.branch_taken(side_taken),')
 s=rep(s,'wire[64:0] side_result={side_execute,secondary_result[244:213],secondary_result[180:149]};',
  "wire[31:0] side_value=side_branch ? secondary_result[212:181] : side_multiply ? 32'b0 : secondary_result[180:149];\n wire[64:0] side_result={side_execute,secondary_result[244:213],side_value};")
 s=s.replace('ex_fire && side_execute && secondary_result[15:11]!=0', 'ex_fire && side_execute && !side_branch && !side_multiply && secondary_result[15:11]!=0')
 s=rep(s,'wire branch_event=ex_fire && prediction_wrong;', 'wire branch_event=ex_fire && (prediction_wrong || (side_branch && !execute_packet[2] && side_wrong));')
 s=rep(s,'bp_update_pc<=execute_packet[276:245];bp_update_target<=execute_target;', 'bp_update_pc<=side_branch ? secondary_result[276:245] : execute_packet[276:245];bp_update_target<=resolved_target;')
 s=rep(s,'bp_update_branch<=ex_branch;bp_update_conditional<=execute_packet[7:4]==1;', 'bp_update_branch<=resolved_branch;bp_update_conditional<=side_branch || execute_packet[7:4]==1;')
 s=s.replace('bp_update_taken<=execute_taken;', 'bp_update_taken<=resolved_taken;')
 s=s.replace('(ex_branch || ex_prediction[31])', '(resolved_branch || ex_prediction[31])')
 s=rep(s,"(commit && w_kind>=1 && w_kind<=3),branch_event,", "((commit && w_kind>=1 && w_kind<=3) || (commit1 && w1_branch)),branch_event,")
 s=rep(s,'destination1[tail]<=pair_candidate ? rd1 : 0;', 'destination1[tail]<=pair_candidate && id1_wr ? rd1 : 0;')
 s=rep(s,"commit1 ? w1_pc+32'd4 : w_next", "commit1 ? (w1_branch ? w1_result : w1_pc+32'd4) : w_next")
 s=rep(s,'redirect_pc<=execute_packet[212:181];', 'redirect_pc<=side_branch ? secondary_result[212:181] : execute_packet[212:181];')
 if mul:
  s=rep(s,'wire m_valid;wire[2:0] m_tag;', 'wire m_valid,m_lane;wire[2:0] m_tag;')
  s=s.replace('.m_tag({m_tag,1\'b0})', '.m_tag({m_tag,m_lane})')
  s=rep(s,'wire mul_accept=ex_fire && ex_multiply;', '''wire mul_accept=ex_fire && (ex_multiply || (side_multiply && side_execute));
 wire[31:0] mul_a=side_multiply ? ex_side[135:104] : ex_packet[135:104];
 wire[31:0] mul_b=side_multiply ? ex_side[103:72] : ex_packet[103:72];
 wire[1:0] mul_op=side_multiply ? ex_side[149:148] : ex_packet[149:148];''')
  s=rep(s,'.in_tag(ex_tag),.operation(ex_packet[149:148]),.a(ex_packet[135:104]),.b(ex_packet[103:72]),', '.in_tag(ex_tag),.in_lane(side_multiply),.forward_lane(m_lane),.operation(mul_op),.a(mul_a),.b(mul_b),')
  m=(ROOT/'hardware/pds/source/core/nc_mul_pipeline.v').read_text()
  m=rep(m,'input wire[2:0] in_tag,', 'input wire in_lane,output reg forward_lane,input wire[2:0] in_tag,')
  m=rep(m,'reg v0,v1,v2;', 'reg lane0,lane1,lane2;reg v0,v1,v2;')
  m=m.replace('if(accept) begin aa<=a;', 'if(accept) begin lane0<=in_lane;aa<=a;').replace('if(v0) begin p_ll<=ll;', 'if(v0) begin lane1<=lane0;p_ll<=ll;').replace('if(v1) begin\n   low2<=', 'if(v1) begin\n   lane2<=lane1;low2<=')
  m=rep(m,'forward_tag<=low_done ? tag1 : tag2;', 'forward_tag<=low_done ? tag1 : tag2;forward_lane<=low_done ? lane1 : lane2;')
  (out/'nc_mul_pipeline.v').write_text(m)
  m=(out/'nc_memory.v').read_text()
  m=rep(m,'wire input_multiply=valid && !packet[2] && packet[7:4]==6 && !packet[10];', '''wire primary_multiply=packet[7:4]==6 && !packet[10];
 wire secondary_multiply=side_packet[64] && side_packet[38:32]==7'h33 && side_packet[63:57]==7'h01 && !side_packet[46];
 wire input_multiply=valid && !packet[2] && (primary_multiply || secondary_multiply);
 wire[64:0] completed_side=secondary_multiply ? {side_packet[64:32],mul_data} : side_packet;''')
  m=m.replace('? held_side : side_packet;', '? held_side : completed_side;').replace('completed_input=input_multiply ?', 'completed_input=primary_multiply ?').replace('held_side<=side_packet;', 'held_side<=completed_side;')
  (out/'nc_memory.v').write_text(m)
 (out/'nc_core.v').write_text(s)
 for file in ('nc_core.v','nc_fetch.v','nc_execute.v')+(('nc_memory.v','nc_mul_pipeline.v') if mul else ()):
  g['override_sha256']['hardware\\pds\\source\\core\\'+file]=sha(out/file)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope=a.variant+'; primary plain ALU for extended pairs; conditional branch aligned target and/or shared MUL; ordinary side ALU policy unchanged; no new operand waits or LSU')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',a.variant)
if __name__=='__main__':main()
