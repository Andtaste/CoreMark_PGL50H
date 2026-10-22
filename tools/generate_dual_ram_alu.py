"""Remove unused full secondary decoder; IF-registered legality is unchanged."""
from pathlib import Path
import json,shutil,hashlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/load_bp_dual_ram_logic';dest=src.with_name('load_bp_dual_ram_alu');dest.mkdir(exist_ok=True);meta=json.loads((src/'generation.json').read_text())
 for n,h in meta['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h,n;shutil.copyfile(p,dest/p.name)
 p=dest/'nc_core.v';s=p.read_text();start=s.index('wire[3:0] id1_kind;');end=s.index(' nc_regfile rf(',start)
 s=s[:start]+'''// Only legal plain ALUs can enter lane1; IF-registered pair flags
 // remain authoritative. No second CSR/branch/load legality network.
 wire[31:0] c,d;reg[31:0] id1_imm;reg[18:0] id1_control;
 wire[4:0] rs1_1=id_insn1[19:15],rs2_1=id_insn1[24:20],rd1=id_insn1[11:7];
 wire id1_wr=1'b1;wire[6:0] id1_opcode=id_insn1[6:0];
 always @* begin
  id1_imm=(id1_opcode==7'h37 || id1_opcode==7'h17) ? {id_insn1[31:12],12'b0} : {{20{id_insn1[31]}},id_insn1[31:20]};
  id1_control=0;
  if(id1_opcode==7'h37) id1_control[8]=1;
  else if(id1_opcode==7'h17) id1_control[9]=1;
  else id1_control[id_insn1[14:12]]=1;
  id1_control[13]=id1_opcode==7'h33 && id_insn1[14:12]==0 && id_insn1[30];
  id1_control[14]=id_insn1[30];id1_control[15]=id1_opcode==7'h13;
 end
'''+s[end:];p.write_text(s)
 shutil.copytree(src/'ipcore',dest/'ipcore',dirs_exist_ok=True);shutil.copyfile(src/'pango_ram_wide_models.v',dest/'pango_ram_wide_models.v')
 # Constants in copied generated IP are identical; retain the referenced
 # generator input's hash as well as all copied IP source hashes.
 for n in meta['override_sha256']:meta['override_sha256'][n]=sha(dest/Path(n).name)
 ipfiles=[p for p in (dest/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 meta['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ipfiles+[src/'boot_interleaved.hex']};meta['generator_sha256']=sha(Path(__file__));meta['scope']='Same RAM/issue policy as dual_ram_logic; secondary plain-ALU decoder only'
 (dest/'generation.json').write_text(json.dumps(meta,indent=2)+'\n');print('GENERATED',dest.name)
if __name__=='__main__':main()
