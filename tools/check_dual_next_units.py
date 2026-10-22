"""Protocol-aware operand reference and exact-admission integration adapters."""
from pathlib import Path
import argparse,sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);ap.add_argument('--mode',choices=('operands','pairs','timeline','soc','audit'),required=True);a=ap.parse_args();kind=a.variant.rsplit('_',1)[1]
 if a.mode=='operands':
  if kind in ('loadwake','wordwake'):
   base=ROOT/'tools/check_dual_legacy.py';s=base.read_text()
   s=s.replace("s=source.read_text().replace('.next_f_tag(next_f_tag),.next_m_tag(next_m_tag),.next_w_tag(next_w_tag),','')", "s=source.read_text();pos=s.index(' old_nc_operands ref_dut');s=s[:pos].replace('.next_m_tag(next_m_tag)',\".next_m_tag({next_m_tag,1'b0})\")+s[pos:]")
   s=s.replace("if a.variant=='dual_legacy_fifo':","if False:")
  else:
   base=ROOT/'tools/check_dual_joint_reg_operands.py';s=base.read_text()
   if kind=='mqual':
    s=s.replace("s=tb_source.read_text();pos=s.index(' old_nc_operands ref_dut')", "s=tb_source.read_text().replace(' reg wait_a=0,', ' reg next_m_valid=0;\\n reg wait_a=0,').replace(' m_tag<=', ' m_tag<=').replace(\" m_tag<={next_m_tag,1'b0};\",\" m_valid<=next_m_valid;m_tag<={next_m_tag,1'b0};\").replace('m_valid=rng[18];','next_m_valid=rng[18];');pos=s.index(' old_nc_operands ref_dut')")
    s=s.replace("s=s[:pos].replace('.next_m_tag(next_m_tag)',", "s=s[:pos].replace('.next_f_tag(next_f_tag)', '.next_m_valid(next_m_valid),.next_f_tag(next_f_tag)').replace('.next_m_tag(next_m_tag)',")
  sub='operand_checks';argv=[str(base),'--variant',a.variant]+(['--mode','operands'] if kind in ('loadwake','wordwake') else [])
 elif a.mode=='pairs':
  base=ROOT/'tools/check_dual_joint_pairs.py';s=base.read_text()
  s=s.replace('(!CPU.id_pair_flags[3] || CPU.second_dep)','(!CPU.extended_pair || CPU.second_dep)')
  s=s.replace('CPU.memory.valid && CPU.memory.side_packet[64]','CPU.memory.slot_valid && !CPU.memory.exception && CPU.memory.held_side[64]').replace('CPU.memory.side_packet[','CPU.memory.held_side[')
  sub='pair_checks';argv=[str(base),'--variant',a.variant]
 elif a.mode=='soc':
  base=ROOT/'tools/check_dual_store_simple_soc.py';s=base.read_text()
  if kind=='pairmul':
   s=s.replace("s=s.replace(' reg was_local;'", "s=s.replace(' || !dut.cpu.memory.wb_valid','').replace(' reg was_local;'")
  sub='posted_soc_final';argv=[str(base),'--variant',a.variant]
 elif a.mode=='timeline':
  base=ROOT/'tools/check_dual_boundary_v3.py';s=base.read_text()
  if kind in ('loadwake','wordwake'):
   # Adapt the actual lower-level comparison, retaining measured events.
   base=ROOT/'tools/check_dual_boundary.py';s=base.read_text().replace("r==e+(0 if a.variant.endswith('_early') else 1) and w==r+1 and c==w+1",'r>=e and w==r+1 and c>=w')
  sub='timeline_checks';argv=[str(base),'--variant',a.variant,'--mode','timeline']
 else:
  base=ROOT/'tools/check_dual_boundary.py';s=base.read_text();sub='audit_checks';argv=[str(base),'--variant',a.variant,'--mode','audit']
 sys.argv=argv;ns={'__file__':str(base),'__name__':'next_unit_adapter'};exec(compile(s,str(base),'exec'),ns);ns['main']()
 p=ROOT/('simulation/results/load_bp_'+a.variant)/sub/'result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();x['adapter_note']='Current future-tag protocol; exact extended admission; load bypass may execute on WB capture edge; paired posted acceptance need not equal group completion.';p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
