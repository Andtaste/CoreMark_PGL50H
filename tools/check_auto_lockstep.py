"""Compare current-board reference and candidate with independently instantiated RTL."""
from pathlib import Path
import argparse,json,re,subprocess,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--reference',default='original_board');a=p.parse_args()
 src=ROOT/f'simulation/results/autonomous_20261022/{a.name}'
 ref=src.parent/a.reference/'source/core'
 out=src/'lockstep';out.mkdir(exist_ok=True)
 gold=out/'gold.v';gold.write_text('\n'.join(re.sub(r'\bnc_', 'gold_nc_',p.read_text()) for p in sorted(ref.glob('*.v'))))
 bench=ROOT/f'simulation/results/load_bp_dual_boundary_auto_{a.name}/checks/core_tb.v'
 s=bench.read_text();start=s.index(' nc_core dut(');end=s.index(';',start)+1;inst=s[start:end]
 for sig in ['iv','ia','iready','dv','da','dw','mask','dwrite','dready','tv','tt','tp','ti','td','tc','tr']:
  inst=inst.replace('('+sig+')','(gold_'+sig+')')
 inst=inst.replace('nc_core dut(', 'gold_nc_core golden(')
 mon='''
 wire gold_iv,gold_iready,gold_dv,gold_dwrite,gold_dready,gold_tv,gold_tt;
 wire[31:0] gold_ia,gold_da,gold_dw,gold_tp,gold_ti,gold_td,gold_tc;
 wire[3:0] gold_mask;wire[4:0] gold_tr;
 INSTANCE
 always @(negedge clk) if(rst_n) begin
  if({iv,iready,dv,dready,tv,dut.trace1_valid} !== {gold_iv,gold_iready,gold_dv,gold_dready,gold_tv,golden.trace1_valid}) $fatal(1,"Lockstep handshake mismatch");
  if(iv && ia!==gold_ia) $fatal(1,"Lockstep fetch mismatch");
  if(dv && {da,dw,mask,dwrite}!=={gold_da,gold_dw,gold_mask,gold_dwrite}) $fatal(1,"Lockstep request mismatch");
  if(tv && {tt,tp,ti,td,tc,tr}!=={gold_tt,gold_tp,gold_ti,gold_td,gold_tc,gold_tr}) $fatal(1,"Lockstep primary retirement mismatch");
  if(dut.trace1_valid && {dut.trace1_pc,dut.trace1_insn,dut.trace1_rd,dut.trace1_data}!=={golden.trace1_pc,golden.trace1_insn,golden.trace1_rd,golden.trace1_data}) $fatal(1,"Lockstep secondary retirement mismatch");
  if(finish_count==1) $display("LOCKSTEP_PASS cycles=%0d",ticks);
 end
 '''.replace('INSTANCE',inst)
 tb=out/'core_tb.v';tb.write_text(s.replace('endmodule',mon+'\nendmodule'))
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
 inputs=[*sorted((src/'source/core').glob('*.v')),gold,tb]
 def run(cmd,name):
  x=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180)
  (out/(name+'.log')).write_bytes(x.stdout+x.stderr);assert x.returncode==0,(name,x.stdout[-2000:],x.stderr[-2000:]);return x.stdout
 run([iv,'-g2012','-s','core_tb','-o',out/'sim.vvp',*inputs],'compile')
 tests=[]
 for n in ('directed','prediction','random_17','random_91','random_2026'):
  image=ROOT/f'simulation/results/{n}.hex';inputs.append(image)
  for seed in (37,613):
   name=f'{n}_{seed}';t=run([vvp,out/'sim.vvp',f'+image={image}',f'+trace={out}/{name}.trace',f'+seed={seed}'],name)
   assert b'LOCKSTEP_PASS' in t;tests.append(name)
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}),indent=2))
 print(a.name,'PASS',len(tests),'cycle lockstep cases')
if __name__=='__main__':main()
