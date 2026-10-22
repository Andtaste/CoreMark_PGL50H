"""Register the two-instruction view; retain group ownership separately."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_window_cross','dual_window_both'),required=True);a=ap.parse_args()
 src=ROOT/('simulation/results/load_bp_dual_admit_'+a.variant.rsplit('_',1)[1]);out=src.with_name('load_bp_'+a.variant);out.mkdir(exist_ok=True)
 meta=json.loads((src/'generation.json').read_text())
 for n,h in meta['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h,n;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore',dirs_exist_ok=True);shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 s=(out/'nc_fetch.v').read_text()
 s=s.replace('pack_flags(cross_window ? peek_parts[7:0] : head_parts[15:8])','pack_flags(head_parts[15:8])')
 start=s.index(' wire cross_window=');end=s.index(';',start)+1
 s=s[:start]+' reg head_cross;wire cross_window=head_cross;'+s[end:]
 s=s.replace('assign inst1=cross_window ? peek_inst[31:0] : head_inst[63:32];','assign inst1=head_inst[63:32];')
 s=s.replace('assign prediction1=cross_window ? peek_predictions[31:0] : head_predictions[63:32];','assign prediction1=head_predictions[63:32];')
 start=s.index(' always @(posedge clk) begin\n  if(push)');end=s.index(' always @(posedge clk or negedge rst_n)',start)
 block=''' // This function forms a view BEFORE the head registers. Instruction
 // class, instruction bits, prediction and cross ownership are all sampled
 // on the same edge. ID sees no head/peek data mux or late fault gate.
 function[178:0] frame;
  input[15:0] gp,np;input[63:0] gi,ni;input[33:0] gm,nm;
  input[63:0] gr,nr;input nv;
  reg borrow;
  begin
   borrow=!gm[33] && gm[2] && !gm[32] && !gr[30] && nv && nm[33] && !nm[32];
   frame={borrow,(borrow ? {np[7:0],gp[7:0]} : gp),
                (borrow ? {ni[31:0],gi[31:0]} : gi),gm,
                (borrow ? {nr[31:0],gr[31:0]} : gr)};
  end
 endfunction
 wire near_valid=count>1 || push;
 wire[15:0] near_parts=count>1 ? peek_parts : incoming_flags;
 wire[63:0] near_inst=count>1 ? peek_inst : incoming;
 wire[33:0] near_meta=count>1 ? peek_meta : incoming_meta;
 wire[63:0] near_predictions=count>1 ? peek_predictions : incoming_predictions;
 wire far_valid=count>2 || (count==2 && push);
 wire[15:0] far_parts=count>2 ? flags[after_following] : incoming_flags;
 wire[63:0] far_inst=count>2 ? instructions[after_following] : incoming;
 wire[33:0] far_meta=count>2 ? metadata[after_following] : incoming_meta;
 wire[63:0] far_predictions=count>2 ? predictions[after_following] : incoming_predictions;
 always @(posedge clk) begin
  if(push) begin flags[wr]<=incoming_flags;instructions[wr]<=incoming;metadata[wr]<=incoming_meta;predictions[wr]<=incoming_predictions;end
  if(consume) begin
   if(group_two && !take_two) begin
    {head_cross,head_parts,head_inst,head_meta,head_predictions}<=frame(
     {8'b0,head_parts[15:8]},near_parts,{32'b0,head_inst[63:32]},near_inst,
     {1'b0,head_meta[32],pc+32'd4},near_meta,{32'b0,head_predictions[63:32]},near_predictions,near_valid);
   end else if(cross_window && take_two) begin
    {head_cross,head_parts,head_inst,head_meta,head_predictions}<=frame(
     {8'b0,peek_parts[15:8]},far_parts,{32'b0,peek_inst[63:32]},far_inst,
     {1'b0,peek_meta[32],peek_meta[31:0]+32'd4},far_meta,{32'b0,peek_predictions[63:32]},far_predictions,far_valid);
   end else if(count>1) begin
    {head_cross,head_parts,head_inst,head_meta,head_predictions}<=frame(
     peek_parts,far_parts,peek_inst,far_inst,peek_meta,far_meta,peek_predictions,far_predictions,far_valid);
   end else begin
    {head_cross,head_parts,head_inst,head_meta,head_predictions}<=frame(
     push ? incoming_flags : 16'b0,16'b0,push ? incoming : 64'b0,64'b0,
     push ? incoming_meta : 34'b0,34'b0,push ? incoming_predictions : 64'b0,64'b0,1'b0);
   end
  end else if(push && count==0) begin
   {head_cross,head_parts,head_inst,head_meta,head_predictions}<=frame(
    incoming_flags,16'b0,incoming,64'b0,incoming_meta,34'b0,incoming_predictions,64'b0,1'b0);
  end else if(push && count==1) begin
   {head_cross,head_parts,head_inst,head_meta,head_predictions}<=frame(
    head_parts,incoming_flags,head_inst,incoming,head_meta,incoming_meta,head_predictions,incoming_predictions,1'b1);
  end
 end
'''
 s=s[:start]+block+s[end:];(out/'nc_fetch.v').write_text(s)
 meta['override_sha256']['hardware\\pds\\source\\core\\nc_fetch.v']=sha(out/'nc_fetch.v')
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 meta['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 meta.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope='Registered cross-group view refinement of '+src.name+'; same four groups, two ALUs and one LSU')
 (out/'generation.json').write_text(json.dumps(meta,indent=2)+'\n');print('GENERATED',a.variant)
if __name__=='__main__':main()
