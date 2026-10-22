"""Restrict raw return data to separate ALU inputs; AGU/branch keep registered sources."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 accepted=ROOT/'docs/accepted_dual_baseline.json';src=ROOT/'simulation/results/load_bp_dual_boundary_next_loadcapture';out=src.with_name('load_bp_dual_boundary_next_aluwake');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v');c=(out/'nc_core.v').read_text();o=(out/'nc_operands.v').read_text();e=(out/'nc_execute.v').read_text()
 o=rep(o,' output wire occupied);',' output wire occupied,output wire[31:0] out_alu_a,out_alu_b,out_alu_c,out_alu_d);')
 o=rep(o,' genvar s;', ''' wire[1:0] alu_return;
 genvar s;''')
 o=rep(o,'  // Match each physical slot', '''  // Current-cycle return eligibility is restricted to ALU-only groups.
  // Returned data has separate physical ALU outputs; it cannot drive AGU
  // address, branch comparison, target selection or CSR operands.
  assign alu_return[s]=payload[s][203:200]==0 && (!side[s][223] || side[s][203:200]==0);
  // Match each physical slot''')
 body=''
 for op in 'abcd':
  o=rep(o,f'  assign available_{op}[s]=',f'  wire alu_r_{op}=alu_return[s] && r_valid && r_tag==dep_{op}[s];\n  assign available_{op}[s]=alu_r_{op} || ')
  selected={'a':'selected_va[rd]','b':'selected_vb[rd]','c':'selected_c[rd]','d':'selected_d[rd]'}[op]
  high=f'(hit_f{op}[rd] || hit_f1{op}[rd] || hit_m{op}[rd])' if op in 'ab' else f'((sf_{op}[rd] && f_valid) || (sf1_{op}[rd] && f1_valid) || (sm_{op}[rd] && m_valid))'
  body+=f' assign out_alu_{op}=(w{op}[rd] && alu_return[rd] && r_valid && r_tag==dep_{op}[rd] && !{high}) ? r_data : {selected};\n'
 o=rep(o,' wire[31:0] a=selected_va[rd],b=selected_vb[rd];',body+' wire[31:0] a=selected_va[rd],b=selected_vb[rd];')
 c=rep(c,' wire[223:0] ex_side;',' wire[31:0] alu_a,alu_b,alu_c,alu_d;\n wire[223:0] ex_side;')
 c=rep(c,'.occupied(ex_occupied));','.occupied(ex_occupied),.out_alu_a(alu_a),.out_alu_b(alu_b),.out_alu_c(alu_c),.out_alu_d(alu_d));')
 c=rep(c,'.packet(ex_packet),.control(ex_control)', '.packet(ex_packet),.alu_a(alu_a),.alu_b(alu_b),.control(ex_control)')
 c=rep(c,'.packet(ex_side[203:0]),.control(','.packet(ex_side[203:0]),.alu_a(alu_c),.alu_b(alu_d),.control(')
 e=rep(e,' input wire[203:0] packet,',' input wire[31:0] alu_a,alu_b,\n input wire[203:0] packet,')
 e=rep(e,' wire[31:0] rhs=control[15] ? imm : b;', ' wire[31:0] rhs=control[15] ? imm : alu_b;')
 for old,new in [('add_value=a+','add_value=alu_a+'),('left_value=a<<','left_value=alu_a<<'),('control[14] && a[31],a','control[14] && alu_a[31],alu_a'),('$signed(a)<$signed(rhs)','$signed(alu_a)<$signed(rhs)'),('{31\'b0,a<rhs}',"{31'b0,alu_a<rhs}"),('(a^rhs)','(alu_a^rhs)'),('(a|rhs)','(alu_a|rhs)'),('(a&rhs)','(alu_a&rhs)')]:e=rep(e,old,new)
 for name,s in (('nc_core.v',c),('nc_operands.v',o),('nc_execute.v',e)):(out/name).write_text(s)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),accepted_dual_sha256=sha(accepted),trial='aluwake',scope='Capture-only family plus ALU-only same-cycle return on physically separate ALU data ports; original AGU/branch/CSR operand data retained; no return-data-to-address/control path; return-valid-to-issue path remains; NOT ADOPTED')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',out.name)
if __name__=='__main__':main()
