"""Isolated registered-WB admission and registered following-group cross pairing."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_admit_base','dual_admit_wb','dual_admit_cross','dual_admit_both'),required=True);a=ap.parse_args()
 src=ROOT/'simulation/results/load_bp_dual_fwd_share';out=src.with_name('load_bp_'+a.variant);out.mkdir(exist_ok=True)
 meta=json.loads((src/'generation.json').read_text())
 for n,h in meta['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h,n;shutil.copyfile(p,out/p.name)
 for n,h in meta['ip_sha256'].items():assert sha(ROOT/n)==h,n
 shutil.copytree(src/'ipcore',out/'ipcore',dirs_exist_ok=True);shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 if a.variant in ('dual_admit_wb','dual_admit_both'):
  s=(out/'nc_core.v').read_text()
  old="""    if((id_pair_flags[5] && rs1_1!=0 && (destination[n]==rs1_1 || destination1[n]==rs1_1)) ||
       (id_pair_flags[6] && rs2_1!=0 && (destination[n]==rs2_1 || destination1[n]==rs2_1))) second_dep=1;"""
  new="""    // Only registered WB may satisfy a secondary operand in ID.
    // Other matching live writers still block, including younger WAWs.
    if(id_pair_flags[5] && rs1_1!=0 &&
      ((destination[n]==rs1_1 && !(commit && w_wr && w_tag==n[2:0])) ||
       (destination1[n]==rs1_1 && !(commit1 && w_tag==n[2:0])))) second_dep=1;
    if(id_pair_flags[6] && rs2_1!=0 &&
      ((destination[n]==rs2_1 && !(commit && w_wr && w_tag==n[2:0])) ||
       (destination1[n]==rs2_1 && !(commit1 && w_tag==n[2:0])))) second_dep=1;"""
  assert old in s;s=s.replace(old,new)
  old=" wire[223:0] id_side={pair_candidate,id1_control,4'b0,id_pc+32'd4,id_insn1,c,d,id1_imm,32'b0,rd1,id1_wr,2'b0};"
  new=""" // Registered writeback data terminates at the existing ID/EX sidecar.
 wire wb_a0=commit && w_wr && rs1_1!=0 && w_rd==rs1_1;
 wire wb_a1=commit1 && rs1_1!=0 && w1_rd==rs1_1;
 wire wb_b0=commit && w_wr && rs2_1!=0 && w_rd==rs2_1;
 wire wb_b1=commit1 && rs2_1!=0 && w1_rd==rs2_1;
 wire[31:0] side_a=wb_a1 ? w1_result : wb_a0 ? w_result : c;
 wire[31:0] side_b=wb_b1 ? w1_result : wb_b0 ? w_result : d;
 wire[223:0] id_side={pair_candidate,id1_control,4'b0,id_pc+32'd4,id_insn1,side_a,side_b,id1_imm,32'b0,rd1,id1_wr,2'b0};"""
  assert old in s;s=s.replace(old,new);(out/'nc_core.v').write_text(s)
 if a.variant in ('dual_admit_cross','dual_admit_both'):
  s=(out/'nc_fetch.v').read_text()
  s=s.replace('reg[15:0] head_parts;assign pair_flags={pack_flags(head_parts[15:8]),pack_flags(head_parts[7:0])};',
    'reg[15:0] head_parts;assign pair_flags={pack_flags(cross_window ? peek_parts[7:0] : head_parts[15:8]),pack_flags(head_parts[7:0])};')
  s=s.replace(' reg[1:0] rd,wr;reg[2:0] count;',""" // Registered following-group cache. Instruction RAM never feeds ID
 // directly. The FIFO retains four groups and its original credit rule.
 reg[63:0] peek_inst,peek_predictions;reg[15:0] peek_parts;reg[33:0] peek_meta;
 reg[1:0] rd,wr;reg[2:0] count;
 wire group_two=head_meta[33];
 // A high-word fall-through command is followed by the next aligned group.
 // A taken prediction disables this window; redirects discard the queue.
 // Require two words in the following group so consuming its low word
 // leaves one group at the new head, without a two-entry pop operation.
 wire cross_window=!group_two && pc[2] && count>1 && !head_meta[32] &&
                    !head_predictions[30] && !peek_meta[32] && peek_meta[33];
 wire[1:0] after_following=rd+2'd2;""")
  s=s.replace('wire pop=consume && (!second_valid || take_two);','wire pop=consume && (!group_two || take_two);')
  s=s.replace('assign valid=count!=0;assign {second_valid,fault,pc}=head_meta;',
    'assign valid=count!=0;assign second_valid=group_two || cross_window;assign {fault,pc}=head_meta[32:0];')
  s=s.replace('assign inst=head_inst[31:0];assign inst1=head_inst[63:32];',
    'assign inst=head_inst[31:0];assign inst1=cross_window ? peek_inst[31:0] : head_inst[63:32];')
  s=s.replace('assign prediction=head_predictions[31:0];assign prediction1=head_predictions[63:32];',
    'assign prediction=head_predictions[31:0];assign prediction1=cross_window ? peek_predictions[31:0] : head_predictions[63:32];')
  s=s.replace('if(second_valid && !take_two) begin','if(group_two && !take_two) begin')
  old="""   end else if(count>1) begin
    head_parts<=flags[following];head_inst<=instructions[following];head_meta<=metadata[following];head_predictions<=predictions[following];"""
  new="""   end else if(cross_window && take_two) begin
    head_parts<={8'b0,peek_parts[15:8]};head_inst<={32'b0,peek_inst[63:32]};
    head_meta<={1'b0,peek_meta[32],peek_meta[31:0]+32'd4};head_predictions<={32'b0,peek_predictions[63:32]};
   end else if(count>1) begin
    head_parts<=peek_parts;head_inst<=peek_inst;head_meta<=peek_meta;head_predictions<=peek_predictions;"""
  assert old in s;s=s.replace(old,new)
  s=s.replace(" wire[1:0] following=rd+2'd1;",'')
  needle=' always @(posedge clk) begin\n  if(push)'
  insert=""" always @(posedge clk) begin
  if(pop && count>2) begin
   peek_inst<=instructions[after_following];peek_parts<=flags[after_following];
   peek_meta<=metadata[after_following];peek_predictions<=predictions[after_following];
  end else if(push && ((!pop && count==1) || (pop && count==2))) begin
   peek_inst<=incoming;peek_parts<=incoming_flags;peek_meta<=incoming_meta;peek_predictions<=incoming_predictions;
  end
 end
 always @(posedge clk) begin
  if(push)"""
  assert needle in s;s=s.replace(needle,insert,1)
  (out/'nc_fetch.v').write_text(s)
 for file in ('nc_core.v','nc_fetch.v'):
  meta['override_sha256']['hardware\\pds\\source\\core\\'+file]=sha(out/file)
 ips=[q for q in (out/'ipcore').rglob('*') if q.is_file() and q.suffix in ('.v','.idf')]
 meta['ip_sha256']={str(q.relative_to(ROOT)):sha(q) for q in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 meta.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope=a.variant+'; accepted dual_fwd_share parent; WB-only side forwarding and/or registered following-group cache; no second LSU or EX-to-ID bypass')
 (out/'generation.json').write_text(json.dumps(meta,indent=2)+'\n');print('GENERATED',a.variant)
if __name__=='__main__':main()
