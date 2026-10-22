"""Six-source independent storage reference, compare effective separate ALU operands."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];base=ROOT/'tools/check_dual_legacy.py';s=base.read_text();v='dual_boundary_next_aluwake'
old="s=source.read_text().replace('.next_f_tag(next_f_tag),.next_m_tag(next_m_tag),.next_w_tag(next_w_tag),','')"
new=r'''s=source.read_text();pos=s.index(' old_nc_operands ref_dut')
  s=s[:pos].replace('.next_m_tag(next_m_tag)',".next_m_tag({next_m_tag,1'b0})")+s[pos:]
  s=s.replace(' wire ready0,ready1,valid0,valid1,occupied0,occupied1;', ' wire[203:0] rawpacket0;wire[223:0] rawside0;wire[31:0] aa0,ab0,ac0,ad0;\n wire ready0,ready1,valid0,valid1,occupied0,occupied1;')
  pos=s.index(' old_nc_operands ref_dut')
  s=s[:pos].replace('.out_packet(packet0)', '.out_packet(rawpacket0),.out_alu_a(aa0),.out_alu_b(ab0),.out_alu_c(ac0),.out_alu_d(ad0)').replace('.out_side(side0)', '.out_side(rawside0)')+s[pos:]
  s=s.replace(' task compare;', ' assign packet0={rawpacket0[203:136],aa0,ab0,rawpacket0[71:0]};\n assign side0={rawside0[223:136],ac0,ad0,rawside0[71:0]};\n task compare;')
  s=s.replace('   #1;compare;', '   in_packet[203:200]=0;in_side[203:200]=0;\n   #1;compare;')'''
assert s.count(old)==1;s=s.replace(old,new)
sys.argv=[str(base),'--variant',v,'--mode','operands'];ns={'__file__':str(base),'__name__':'separate_alu_operand_model'};exec(compile(s,str(base),'exec'),ns);ns['main']()
p=ROOT/('simulation/results/load_bp_'+v+'/operands_checks/result.json');x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();x['scope']='300000-cycle six-source independent storage model on ALU-only groups; compare effective separate ALU operands plus all metadata/valid; non-ALU capture contract covered by capture-only model and full-core regression';p.write_text(json.dumps(x,indent=2)+'\n')
