"""Register static pair class/use bits with each fetched word, before ID."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 src=ROOT/'simulation/results/load_bp_dual_issue_finish';dest=src.with_name('load_bp_dual_issue_predecode');dest.mkdir(exist_ok=True)
 meta=json.loads((src/'generation.json').read_text())
 for n,h in meta['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h,n;shutil.copyfile(p,dest/p.name)
 p=dest/'nc_fetch.v';s=p.read_text()
 s=rep(s,'output wire valid,input wire ready,input wire take_two,output wire second_valid,',
  'output wire[9:0] pair_flags,\n output wire valid,input wire ready,input wire take_two,output wire second_valid,')
 s=rep(s,'reg[63:0] head_inst,head_predictions;reg[33:0] head_meta;', '''// {primary eligible, plain ALU legal, writes rd, use2, use1}.
 // These bits terminate at the same registered FIFO/cache boundary as
 // instructions, never through an EX/LSU-ready dependent predecode path.
 function[4:0] classify;
  input[31:0] insn;
  reg[6:0] op,f7;reg[2:0] f3;reg alu,primary;
  begin
   op=insn[6:0];f7=insn[31:25];f3=insn[14:12];
   alu=op==7'h37 || op==7'h17 ||
    (op==7'h13 && !(f3==1 && f7!=0) && !(f3==5 && f7!=0 && f7!=7'h20)) ||
    (op==7'h33 && (f7==0 || (f7==7'h20 && (f3==0 || f3==5))));
   primary=alu || (op==7'h03 && (f3==0 || f3==1 || f3==2 || f3==4 || f3==5)) ||
    (op==7'h23 && f3<=2) || (op==7'h33 && f7==1 && !f3[2]);
   classify={primary,alu,op!=7'h23,op==7'h33,op==7'h13 || op==7'h33};
  end
 endfunction
 reg[9:0] flags[0:3] /* synthesis syn_ramstyle="registers" */;
 reg[9:0] head_flags;assign pair_flags=head_flags;
 wire[9:0] incoming_flags=flight_pc[2] ? {5'b0,classify(rsp_data[63:32])} :
                                               {classify(rsp_data[63:32]),classify(rsp_data[31:0])};
 reg[63:0] head_inst,head_predictions;reg[33:0] head_meta;''')
 s=rep(s,'if(push) begin instructions[wr]<=incoming;','if(push) begin flags[wr]<=incoming_flags;instructions[wr]<=incoming;')
 s=rep(s,"head_inst<={32'b0,head_inst[63:32]};", "head_flags<={5'b0,head_flags[9:5]};head_inst<={32'b0,head_inst[63:32]};")
 s=rep(s,'head_inst<=instructions[following];','head_flags<=flags[following];head_inst<=instructions[following];')
 s=rep(s,"head_inst<=push ? incoming : 64'b0;", "head_flags<=push ? incoming_flags : 10'b0;head_inst<=push ? incoming : 64'b0;")
 s=rep(s,'head_inst<=incoming;head_meta<=incoming_meta;', 'head_flags<=incoming_flags;head_inst<=incoming;head_meta<=incoming_meta;')
 p.write_text(s)
 p=dest/'nc_core.v';s=p.read_text()
 s=rep(s,'wire id_valid,id_fault,id_ready,id_second,pair_issue;', 'wire[9:0] id_pair_flags;wire id_valid,id_fault,id_ready,id_second,pair_issue;')
 s=rep(s,'.prediction1(id_prediction1),.inst1(id_insn1),','.pair_flags(id_pair_flags),.prediction1(id_prediction1),.inst1(id_insn1),')
 start=s.index(' // Pair legality has its own opcode-local decode.')
 end=s.index(' wire pair_candidate=',start)
 s=s[:start]+''' // Static pair legality/source-use flags came through the IF response
 // register boundary. Only live dependency comparisons remain in ID.
'''+s[end:]
 s=s.replace('(id1_use1 &&','(id_pair_flags[5] &&').replace('(id1_use2 &&','(id_pair_flags[6] &&')
 s=s.replace('&& primary_pair_legal &&','&& id_pair_flags[4] &&')
 s=s.replace('id1_kind==0 && !id1_illegal && !id1_serial','id_pair_flags[8]')
 s=s.replace('primary_pair_write &&','id_pair_flags[2] &&')
 p.write_text(s)
 for n in meta['override_sha256']:meta['override_sha256'][n]=sha(dest/Path(n).name)
 meta['generator_sha256']=sha(Path(__file__));meta['parent_generation_sha256']=sha(src/'generation.json');meta['scope']='Registered static IF pair flags; identical issue policy to timing-finished candidate'
 (dest/'generation.json').write_text(json.dumps(meta,indent=2)+'\n');print('GENERATED registered IF pair flags')
if __name__=='__main__':main()
