"""Prequalify next-PC alternatives before the late branch comparison."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 accepted=ROOT/'docs/accepted_dual_baseline.json';d=json.loads(accepted.read_text());assert d['variant']=='dual_boundary_storewrite'
 src=ROOT/d['source_directory'];out=src.with_name('load_bp_dual_boundary_pcselect');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_execute.v';s=p.read_text();s=rep(s,' reg[31:0] result,next_pc,tval,csr_data;',' reg[31:0] result,tval,csr_data;')
 s=rep(s,' result=selected_result;next_pc=sequential_pc;tval=0;',' result=selected_result;tval=0;')
 s=rep(s,'   1:if(taken) next_pc=direct_target;\n   2:next_pc=direct_target;\n   3:next_pc=indirect_target;','   1,2,3:;')
 s=rep(s,' wire[31:0] indirect_target={address[31:1],1\'b0};',''' wire[31:0] indirect_target={address[31:1],1'b0};
 // Classify each vector from registered metadata before taken arrives.
 // Only the branch-specific vectors pass through the late direction mux.
 // All instruction classes, including unused kind values, keep old next-PC.
 wire[31:0] fixed_next=({32{kind!=1 && kind!=2 && kind!=3}} & sequential_pc) |
                       ({32{kind==2}} & direct_target) |
                       ({32{kind==3}} & indirect_target);
 wire[31:0] branch_yes_next={32{kind==1}} & direct_target;
 wire[31:0] branch_no_next={32{kind==1}} & sequential_pc;
 wire[31:0] next_pc=fixed_next | (taken ? branch_yes_next : branch_no_next);''');p.write_text(s)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),accepted_dual_sha256=sha(accepted),scope='Only execute next-PC equivalent mux factoring: prequalified fixed and conditional vectors before late taken select; headmux not included; all controls/prediction/fault/handshake/cycles unchanged; not adopted')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED dual_boundary_pcselect')
if __name__=='__main__':main()
