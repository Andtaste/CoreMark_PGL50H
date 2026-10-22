"""Compact two-word sliding window over accepted four-group backing storage."""
from pathlib import Path
import hashlib,json,shutil,argparse
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_types_compact','dual_types_slide'),required=True);a=ap.parse_args()
 src=ROOT/'simulation/results/load_bp_dual_types_both';out=src.with_name('load_bp_'+a.variant);out.mkdir(exist_ok=True);g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h,n;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore',dirs_exist_ok=True);shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 s=(out/'nc_core.v').read_text();s=rep(s,"wire w1_branch=w1_insn[6:0]==7'h63;", '''// Under commit1, admitted ALU/MUL opcodes all have bit6=0 and
 // conditional branch has bit6=1. No full opcode decode on the WB control.
 wire w1_branch=w1_insn[6];''');(out/'nc_core.v').write_text(s)
 s=(out/'nc_memory.v').read_text();s=rep(s,"side_packet[38:32]==7'h33 && side_packet[63:57]==7'h01 && !side_packet[46]", "!side_packet[38] && side_packet[37] && !side_packet[34] && side_packet[57]")
 (out/'nc_memory.v').write_text(s)
 if a.variant=='dual_types_slide':
  s=(out/'nc_fetch.v').read_text()
  s=rep(s,'reg cmd_two,flight_two,cmd_valid,cmd_stale,flight,flight_stale;', '''reg cmd_two,flight_two,cmd_valid,cmd_stale,flight,flight_stale;
 reg cmd_link,flight_link,stream_sequential;reg[3:0] links;
 reg[31:0] peek_inst,peek_prediction;reg[8:0] peek_parts;
 reg peek_two,peek_error,peek_link,peek_valid;
 wire group_two=head_meta[33];
 wire cross_window=!group_two && count>1 && peek_valid && peek_link &&
                   !head_meta[32] && !peek_error && !head_predictions[30];''')
  s=rep(s,'wire[4:0] second_flags=pack_flags(head_parts[17:9]);\n assign pair_flags={head_parts[17],second_flags[3:0],pack_flags(head_parts[8:0])};',
   'wire[8:0] second_parts=cross_window ? peek_parts : head_parts[17:9];\n wire[4:0] second_flags=pack_flags(second_parts);\n assign pair_flags={second_parts[8],second_flags[3:0],pack_flags(head_parts[8:0])};')
  s=rep(s,'wire pop=consume && (!second_valid || take_two);', '''wire pop=consume && (!group_two || take_two);
 wire pop_two_groups=consume && cross_window && take_two && !peek_two;
 wire[1:0] after_following=rd+2'd2;''')
  s=rep(s,'assign valid=count!=0;assign {second_valid,fault,pc}=head_meta;', 'assign valid=count!=0;assign second_valid=group_two || cross_window;assign {fault,pc}=head_meta[32:0];')
  s=rep(s,'assign inst=head_inst[31:0];assign inst1=head_inst[63:32];', 'assign inst=head_inst[31:0];assign inst1=cross_window ? peek_inst : head_inst[63:32];')
  s=rep(s,'assign prediction=head_predictions[31:0];assign prediction1=head_predictions[63:32];', 'assign prediction=head_predictions[31:0];assign prediction1=cross_window ? peek_prediction : head_predictions[63:32];')
  s=rep(s,'if(second_valid && !take_two) begin','if(group_two && !take_two) begin')
  needle='   end else if(count>1) begin\n    head_parts<=flags[following];'
  replacement='''   end else if(cross_window && take_two) begin
    if(peek_two) begin
     head_parts<={9'b0,flags[following][17:9]};head_inst<={32'b0,instructions[following][63:32]};
     head_meta<={1'b0,metadata[following][32],metadata[following][31:0]+32'd4};
     head_predictions<={32'b0,predictions[following][63:32]};
    end else if(count>2) begin
     head_parts<=flags[after_following];head_inst<=instructions[after_following];
     head_meta<=metadata[after_following];head_predictions<=predictions[after_following];
    end else begin
     head_parts<=push ? incoming_flags : 18'b0;head_inst<=push ? incoming : 64'b0;
     head_meta<=push ? incoming_meta : 34'b0;head_predictions<=push ? incoming_predictions : 64'b0;
    end
   end else if(count>1) begin
    head_parts<=flags[following];'''
  s=rep(s,needle,replacement)
  pos=s.index(' always @(posedge clk) begin\n  if(push)')
  s=s[:pos]+''' // Only the following lower word is cached. The upper word stays in
 // backing RAM and terminates at the existing head registers on consume.
 // Reads of following/after_following depend on the registered rd only.
 always @(posedge clk) begin
  if(push) links[wr]<=flight_link;
  if(pop && count>2) begin
   peek_inst<=instructions[after_following][31:0];peek_parts<=flags[after_following][8:0];
   peek_prediction<=predictions[after_following][31:0];peek_two<=metadata[after_following][33];
   peek_error<=metadata[after_following][32];peek_link<=links[after_following];
  end else if(push && ((!pop && count==1) || (pop && count==2))) begin
   peek_inst<=incoming[31:0];peek_parts<=incoming_flags[8:0];peek_prediction<=incoming_predictions[31:0];
   peek_two<=flight_two;peek_error<=rsp_error;peek_link<=flight_link;
  end else if(!peek_valid && count>1 && !pop) begin
   peek_inst<=instructions[following][31:0];peek_parts<=flags[following][8:0];
   peek_prediction<=predictions[following][31:0];peek_two<=metadata[following][33];
   peek_error<=metadata[following][32];peek_link<=links[following];
  end
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin peek_valid<=0;cmd_link<=0;flight_link<=0;stream_sequential<=0;end
  else begin
   if(launch) flight_link<=cmd_link;
   if(prepare) begin cmd_link<=stream_sequential;stream_sequential<=prepare_two ? !lookup_prediction1[30] : !lookup_prediction[30];end
   if(pop_two_groups) peek_valid<=0;
   else if(pop && count>2) peek_valid<=1;
   else if(push && ((!pop && count==1) || (pop && count==2))) peek_valid<=1;
   else if(pop) peek_valid<=0;
   else if(!peek_valid && count>1) peek_valid<=1;
   if(redirect) begin
    peek_valid<=0;stream_sequential<=0;
    if(!cmd_valid || launch) begin cmd_link<=0;stream_sequential<=1;end
   end
  end
 end
'''+s[pos:]
  s=rep(s,"if(push) wr<=wr+1'b1;if(pop) rd<=rd+1'b1;", "if(push) wr<=wr+1'b1;if(pop) rd<=pop_two_groups ? after_following : following;")
  s=rep(s,"case({push,pop}) 2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:;endcase", "count<=count+{2'b0,push}-(pop_two_groups ? 3'd2 : {2'b0,pop});")
  (out/'nc_fetch.v').write_text(s)
 for file in ('nc_core.v','nc_memory.v','nc_fetch.v'):g['override_sha256']['hardware\\pds\\source\\core\\'+file]=sha(out/file)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope=a.variant+'; compact admitted-opcode decode; optional lower-word cache + registered adjacency, consume1/2 words across group boundaries, no native word FIFO rewrite')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',a.variant)
if __name__=='__main__':main()
