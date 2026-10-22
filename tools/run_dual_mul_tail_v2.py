"""Qualify legacy group-only duplicate-value assertions with producer lane."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
def normalize(s,cpu):
 s=s.replace(f'if({cpu}.m_valid && {cpu}.commit &&',f'if({cpu}.m_valid && !{cpu}.m_lane && {cpu}.commit &&')
 s=s.replace(f'if({cpu}.f_valid && {cpu}.m_valid &&',f'if({cpu}.f_valid && {cpu}.m_valid && !{cpu}.m_lane &&')
 mon='''
 always @(posedge clk) if(rst_n) begin
  if(CPU.m_valid && CPU.m_lane && CPU.commit1 && CPU.w1_rd!=0 && CPU.m_tag==CPU.w_tag && CPU.m_data!==CPU.w1_result) $fatal(1,"MUL/W1 same identity differs");
  if(CPU.f1_valid && CPU.m_valid && CPU.m_lane && CPU.f_tag==CPU.m_tag && CPU.f1_data!==CPU.m_data) $fatal(1,"F1/MUL same identity differs");
 end
 '''
 return s.replace('endmodule',mon.replace('CPU',cpu)+'\nendmodule')
def main():
 v=sys.argv[sys.argv.index('--variant')+1];phase=sys.argv[sys.argv.index('--phase')+1]
 base=ROOT/'tools/run_dual_mul_tail.py';s=base.read_text();old="p.read_text().replace('endmodule',MON.replace";assert s.count(old)==1;s=s.replace(old,"normalize(p.read_text(),'dut.cpu' if p.name=='soc_tb.v' else 'dut').replace('endmodule',MON.replace");ns={'__file__':str(base),'__name__':'mul_tail_lanes','normalize':normalize};exec(compile(s,str(base),'exec'),ns);ns['main']();src=ROOT/('simulation/results/load_bp_'+v)
 for p in [src/phase/'result.json']+([src/'result.json'] if phase=='performance' else []):
  x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();x['bench_note']='Legacy group-only MUL/W0 and F0/MUL equality assertions now require lane0; explicit MUL/W1 and F1/MUL lane1 equality assertions added. Retirement differential and future tag checks retained.';p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
