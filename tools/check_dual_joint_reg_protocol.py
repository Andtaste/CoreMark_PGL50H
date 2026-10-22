"""Check the real CPU's future/current producer-tag protocol and side waits."""
from pathlib import Path
import argparse,json,hashlib,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'simulation/scripts/run'));import regression
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args()
 src=ROOT/('simulation/results/load_bp_'+a.variant);out=src/'protocol';out.mkdir(exist_ok=True)
 x=json.loads((src/'checks/result.json').read_text());assert x['status']=='PASS'
 files=[ROOT/n for n in x['actual_compile_sha256'] if Path(n).parent.name in ('core',src.name) and Path(n).name.startswith('nc_')]
 # The candidate directory also contains peripheral overrides; select core names.
 names={p.name for p in (ROOT/'hardware/pds/source/core').glob('*.v')};files=[p for p in files if p.name in names]
 assert len(files)==len(names),(len(files),len(names))
 tb=out/'core_tb.v';original=src/'checks/core_tb.v'
 monitor='''
 reg[2:0] expected_f,expected_w;reg[3:0] expected_m;
 integer pf=0,pm=0,pw=0,side_a=0,side_b=0,side_lane1=0,wait_stall=0;
 always @(posedge clk) if(rst_n) begin
  expected_f=dut.ex_tag;expected_m=dut.m_next_tag;expected_w=dut.future_w_tag;
  if(dut.pair_issue && dut.dep_c) side_a=side_a+1;
  if(dut.pair_issue && dut.dep_d) side_b=side_b+1;
  if(dut.pair_issue && ((dut.dep_c && dut.tag_c[0]) || (dut.dep_d && dut.tag_d[0]))) side_lane1=side_lane1+1;
  if(dut.ex_occupied && !dut.ex_valid) wait_stall=wait_stall+1;
  #1;
  if(dut.f_valid || dut.f1_valid) begin pf=pf+1;if(dut.f_tag!==expected_f) $fatal(1,"F future-tag contract");end
  if(dut.m_valid) begin pm=pm+1;if({dut.m_tag,dut.m_lane}!==expected_m) $fatal(1,"M future-tag contract");end
  if(dut.commit) begin pw=pw+1;if(dut.w_tag!==expected_w) $fatal(1,"W future-tag contract");end
 end
 always @(negedge clk) if(finish_count==1) $display("PROTOCOL_PASS f=%0d m=%0d w=%0d side_a=%0d side_b=%0d side_lane1=%0d wait_stall=%0d",pf,pm,pw,side_a,side_b,side_lane1,wait_stall);
'''
 tb.write_text(original.read_text().replace('endmodule',monitor+'\nendmodule'))
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
 def run(cmd,log):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(out/log).write_bytes(p.stdout+p.stderr)
  assert p.returncode==0,(log,p.stdout[-2000:]);return p.stdout.decode(errors='replace')
 run([iv,'-g2012','-s','core_tb','-o',out/'core.vvp',*files,tb],'compile.log')
 tests=[];inputs=[*files,tb,original,Path(__file__).resolve()]
 for name in ('random_17','random_91','random_2026','prediction'):
  image=ROOT/f'simulation/results/{name}.hex';binary=image.with_suffix('.bin');inputs +=[image,binary]
  for seed in (37,613):
   trace=out/f'{name}_{seed}.trace';s=run([vvp,out/'core.vvp',f'+image={image}',f'+trace={trace}',f'+seed={seed}'],f'{name}_{seed}.log')
   assert 'PASS cycles=' in s and 'PROTOCOL_PASS' in s,s[-2000:]
   data=binary.read_bytes();regression.differential(data+bytes(65536-len(data)),trace)
   tests +=[name+' '+str(seed)+' '+s[s.index('PROTOCOL_PASS'):].splitlines()[0]]
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n')
 print('\n'.join(tests))
if __name__=='__main__':main()
