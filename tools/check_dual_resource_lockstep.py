"""Cycle-accurate parent/candidate comparison under identical random bus stalls."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);ref=ROOT/'simulation/results/load_bp_dual_boundary_next_pairbranch';out=src/'resource_lockstep';out.mkdir(exist_ok=True)
 g=json.loads((src/'generation.json').read_text());actual=[src/p.name if str(p.relative_to(ROOT)) in g['override_sha256'] else p for p in sorted((ROOT/'hardware/pds/source/core').glob('*.v'))]
 # All submodules remain identical to parent; only nc_core storage wiring changes.
 for p in actual:
  if p.name!='nc_core.v' and (ref/p.name).exists():assert sha(p)==sha(ref/p.name),p.name
 gold=out/'gold_core.v';gold.write_text((ref/'nc_core.v').read_text().replace('module nc_core #','module gold_core #',1))
 bench=src/'smoke/core_tb.v';s=bench.read_text();start=s.index(' nc_core dut(');end=s.index(';',start)+1;instance=s[start:end]
 outputs=['iv','ia','iready','dv','da','dw','mask','dwrite','dready','tv','tt','tp','ti','td','tc','tr']
 for signal in outputs:instance=instance.replace('('+signal+')','(gold_'+signal+')')
 instance=instance.replace('nc_core dut(', 'gold_core golden(')
 mon='''
 wire gold_iv,gold_iready,gold_dv,gold_dwrite,gold_dready,gold_tv,gold_tt;
 wire[31:0] gold_ia,gold_da,gold_dw,gold_tp,gold_ti,gold_td,gold_tc;
 wire[3:0] gold_mask;wire[4:0] gold_tr;
 INSTANCE
 integer compared=0;
 always @(negedge clk) if(rst_n) begin
  compared=compared+1;
  if({iv,iready,dv,dready,tv} !== {gold_iv,gold_iready,gold_dv,gold_dready,gold_tv}) $fatal(1,"Lockstep handshake mismatch tick=%0d",ticks);
  if(iv && ia!==gold_ia) $fatal(1,"Lockstep IF address mismatch");
  if(dv && {da,dw,mask,dwrite}!=={gold_da,gold_dw,gold_mask,gold_dwrite}) $fatal(1,"Lockstep data request mismatch");
  if(tv && {tt,tp,ti,td,tc,tr}!=={gold_tt,gold_tp,gold_ti,gold_td,gold_tc,gold_tr}) $fatal(1,"Lockstep retirement mismatch");
  if(dut.ex_occupied && {dut.ex_side,dut.ex_packet,dut.ex_control,dut.ex_prediction} !== {golden.ex_side,golden.ex_packet,golden.ex_control,golden.ex_prediction}) $fatal(1,"Lockstep EX packet/PC mismatch");
  if(dut.mem_valid && {dut.mem_packet,dut.compact_side} !== {golden.mem_packet,golden.compact_side}) $fatal(1,"Lockstep MEM packet mismatch");
  if(finish_count==1) $display("LOCKSTEP_PASS cycles=%0d",compared);
 end
 '''.replace('INSTANCE',instance)
 tb=out/'core_tb.v';tb.write_text(s.replace('endmodule',mon+'\nendmodule'))
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
 x=subprocess.run([str(iv),'-g2012','-s','core_tb','-o',str(out/'sim.vvp'),*map(str,actual),str(gold),str(tb)],capture_output=True,timeout=90);(out/'compile.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0,x.stderr[-2000:]
 inputs=[*actual,ref/'nc_core.v',gold,bench,tb,Path(__file__).resolve()];tests=[]
 images=[ROOT/f'simulation/results/{n}.hex' for n in ('directed','random_17','prediction')]+[ref/f'next_directed/{n}.hex' for n in ('pair_memory','pair_memory_fault')]
 for image in images:
  inputs.append(image)
  for seed in (37,613):
   name=image.stem+'_'+str(seed);x=subprocess.run([str(vvp),str(out/'sim.vvp'),'+image='+str(image),'+trace='+str(out/(name+'.trace')),'+seed='+str(seed)],cwd=ROOT,capture_output=True,timeout=180);(out/(name+'.log')).write_bytes(x.stdout+x.stderr)
   assert x.returncode==0 and b'LOCKSTEP_PASS' in x.stdout,(name,x.stdout[-2500:]);tests.append(name+' PASS')
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,scope='Same-cycle request/response, complete EX and MEM packets, retire trace, random backpressure versus adopted pairbranch; generic non-posted core. Separate SoC suite covers enabled posted writes.',input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print(a.variant,'lockstep PASS',len(tests))
if __name__=='__main__':main()
