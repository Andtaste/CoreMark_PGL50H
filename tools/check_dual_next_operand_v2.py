"""Independent operand storage model under exact future-valid/load-return contracts."""
from pathlib import Path
import argparse,sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);ap.add_argument('--collect-only',action='store_true');a=ap.parse_args();kind=a.variant.rsplit('_',1)[1];src=ROOT/('simulation/results/load_bp_'+a.variant)
 if kind in ('loadwake','wordwake'):
  base=ROOT/'tools/check_dual_next_units.py';s=base.read_text().replace("sub='operand_checks';argv=", "sub='operands_checks' if kind in ('loadwake','wordwake') else 'operand_checks';argv=")
  if a.collect_only:s=s.replace("exec(compile(s,str(base),'exec'),ns);ns['main']()", "exec(compile(s,str(base),'exec'),ns)")
  sys.argv=[str(base),'--variant',a.variant,'--mode','operands'];ns={'__file__':str(base),'__name__':'operand_adapter_postfix'};exec(compile(s,str(base),'exec'),ns);ns['main']();receipt=src/'operands_checks/result.json'
 else:
  base=ROOT/'tools/check_dual_joint_reg_operands.py';s=base.read_text()
  if kind in ('mqual','fqual'):
   prep="s=tb_source.read_text().replace(' reg wait_a=0,', ' reg next_m_valid=0,next_f_valid=0,next_f1_valid=0;\\n reg wait_a=0,').replace('always @(posedge clk) begin','always @(posedge clk) begin m_valid<=next_m_valid;"+('f_valid<=next_f_valid;f1_valid<=next_f1_valid;' if kind=='fqual' else '')+"').replace('m_valid=rng[18];','next_m_valid=rng[18];')"
   if kind=='fqual':prep+=".replace('f_valid=rng[17];','next_f_valid=rng[17];').replace('f1_valid=rng[20];','next_f1_valid=rng[20];')"
   prep+=";pos=s.index(' old_nc_operands ref_dut')"
   ports='.next_m_valid(next_m_valid),'+('.next_f_valid(next_f_valid),.next_f1_valid(next_f1_valid),' if kind=='fqual' else '')
   s=s.replace("s=tb_source.read_text();pos=s.index(' old_nc_operands ref_dut')",prep).replace("s=s[:pos].replace('.next_m_tag(next_m_tag)',", "s=s[:pos].replace('.next_f_tag(next_f_tag)', '"+ports+".next_f_tag(next_f_tag)').replace('.next_m_tag(next_m_tag)',")
  elif kind=='loadcapture':
   prep=r'''s=tb_source.read_text()
 s=s.replace(' reg wait_a=0,', " reg r_valid=0;reg[3:0] r_tag=0;wire[31:0] r_data=32'h89abcdef ^ {28'b0,r_tag};\n reg wait_a=0,")
 s=s.replace('always @(posedge clk) begin','always @(posedge clk) begin w_valid<=r_valid;')
 s=s.replace('w_valid=rng[19];','r_valid=rng[19];').replace('next_w_tag=rng[8:6];','next_w_tag=rng[8:6];r_tag={next_w_tag,1\'b0};')
 s=s.replace('next_w_tag=tag_a[3:1];','next_w_tag=tag_a[3:1];r_tag={next_w_tag,1\'b0};')
 for p in ('f','f1','m','w','w1'):
  s=s.replace(f'{p}_data=0',f'{p}_data=0')
  s=re.sub(r'rng=step\(rng\);'+p+r'_data=rng;','',s)
 s=s.replace('reg[31:0] f1_data=0,w1_data=0;',"wire[31:0] f1_data=32'h89abcdef^{28'b0,f1_tag},w1_data=32'h89abcdef^{28'b0,w1_tag};")
 s=s.replace('reg[31:0] f_data=0,m_data=0,w_data=0;',"wire[31:0] f_data=32'h89abcdef^{28'b0,f_tag},m_data=32'h89abcdef^{28'b0,m_tag},w_data=32'h89abcdef^{28'b0,w_tag};")
 pos=s.index(' old_nc_operands ref_dut')
 s=s[:pos].replace('.f_valid(f_valid)', '.r_valid(r_valid),.r_tag(r_tag),.r_data(r_data),.f_valid(f_valid)')+s[pos:]'''
   s=s.replace("s=tb_source.read_text();pos=s.index(' old_nc_operands ref_dut')",prep)
  else:raise ValueError(kind)
  sys.argv=[str(base),'--variant',a.variant];ns={'__file__':str(base),'__name__':'next_operand_contract'};exec(compile(s,str(base),'exec'),ns)
  if not a.collect_only:ns['main']()
  receipt=src/'operand_checks/result.json'
 x=json.loads(receipt.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();x['contract_note']='Qualified hit: exact next-cycle source valid; capture-only: current load return becomes next-cycle WB with same identity/data, conflicting live broadcasts agree on value. Independent separate operand storage model, valid outputs compared; whole-core arbitrary data tested separately.';receipt.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
