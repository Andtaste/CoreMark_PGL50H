"""Equivalent IF class factoring or partial-predicate registration; no new cycle."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
COMMON='''   op=insn[6:0];f3=insn[14:12];f7=insn[31:25];
   upper=(op & 7'h5f)==7'h17;
   imm_op=op==7'h13;reg_op=op==7'h33;
   zero_f7=f7==0;alt_f7=f7==7'h20;
   // Non-shift immediates do not interpret upper immediate bits as f7.
   base_alu=upper || (imm_op && (f3[1] || !f3[0]));
   zero_alu=(imm_op || reg_op) && zero_f7;
   alt_alu=alt_f7 && ((imm_op && f3==5) || (reg_op && (f3==0 || f3==5)));
   memory_op=(op==7'h03 && (!f3[1] || f3==2)) ||
             (op==7'h23 && !f3[2] && f3[1:0]!=3);
   multiply_op=reg_op && f7==1 && !f3[2];
'''
DECL='''  input[31:0] insn;
  reg[6:0] op,f7;reg[2:0] f3;
  reg upper,imm_op,reg_op,zero_f7,alt_f7;
  reg base_alu,zero_alu,alt_alu,memory_op,multiply_op;
'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_if_class','dual_if_parts'),required=True);a=ap.parse_args()
 src=ROOT/'simulation/results/load_bp_dual_ram_logic';out=src.with_name('load_bp_'+a.variant);out.mkdir(exist_ok=True)
 meta=json.loads((src/'generation.json').read_text())
 for n,h in meta['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h,n;shutil.copyfile(p,out/p.name)
 for n,h in meta['ip_sha256'].items():assert sha(ROOT/n)==h,n
 shutil.copytree(src/'ipcore',out/'ipcore',dirs_exist_ok=True);shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_fetch.v';s=p.read_text();begin=s.index(' function[4:0] classify;');end=s.index(' endfunction',begin)+len(' endfunction')
 if a.variant=='dual_if_class':
  function=' function[4:0] classify;\n'+DECL+'  begin\n'+COMMON+'''   classify={base_alu || zero_alu || alt_alu || memory_op || multiply_op,
             base_alu || zero_alu || alt_alu,op!=7'h23,reg_op,imm_op || reg_op};
  end
 endfunction'''
  s=s[:begin]+function+s[end:]
 else:
  function=' function[7:0] classify_parts;\n'+DECL+'  begin\n'+COMMON+'''   classify_parts={multiply_op,memory_op,alt_alu,zero_alu,base_alu,
                   op!=7'h23,reg_op,imm_op || reg_op};
  end
 endfunction
 function[4:0] pack_flags;
  input[7:0] parts;
  begin pack_flags={|parts[7:3],|parts[5:3],parts[2:0]};end
 endfunction
 // Simulation observability only; synthesized incoming data uses parts.
 function[4:0] classify;
  input[31:0] insn;
  begin classify=pack_flags(classify_parts(insn));end
 endfunction'''
  s=s[:begin]+function+s[end:]
  s=s.replace('reg[9:0] flags[0:3]','reg[15:0] flags[0:3]')
  s=s.replace('reg[9:0] head_flags;assign pair_flags=head_flags;',
   'reg[15:0] head_parts;assign pair_flags={pack_flags(head_parts[15:8]),pack_flags(head_parts[7:0])};')
  old="wire[9:0] incoming_flags=flight_pc[2] ? {5'b0,classify(rsp_data[63:32])} :\n                                               {classify(rsp_data[63:32]),classify(rsp_data[31:0])};"
  new="wire[15:0] incoming_flags=flight_pc[2] ? {8'b0,classify_parts(rsp_data[63:32])} :\n                                               {classify_parts(rsp_data[63:32]),classify_parts(rsp_data[31:0])};"
  assert s.count(old)==1;s=s.replace(old,new)
  s=s.replace('head_flags<=','head_parts<=').replace("{5'b0,head_flags[9:5]}","{8'b0,head_parts[15:8]}").replace("incoming_flags : 10'b0","incoming_flags : 16'b0")
  assert 'head_flags' not in s
 s=s.replace('// Both BTB lookup replicas receive exactly the same registered training.',
  '// Two disjoint PC[2] BTB banks preserve the original 64-entry capacity.')
 p.write_text(s)
 for n in meta['override_sha256']:meta['override_sha256'][n]=sha(out/Path(n).name)
 ips=[q for q in (out/'ipcore').rglob('*') if q.is_file() and q.suffix in ('.v','.idf')]
 meta['ip_sha256']={str(q.relative_to(ROOT)):sha(q) for q in ips+[src/'boot_interleaved.hex']}
 meta.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope=a.variant+'; unchanged instruction ownership, issue policy and fetch latency')
 (out/'generation.json').write_text(json.dumps(meta,indent=2)+'\n');print('GENERATED',a.variant)
if __name__=='__main__':main()
