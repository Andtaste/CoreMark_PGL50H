"""Exercise primary-branch side annulment with real fast SoC memory and traces."""
from pathlib import Path
import argparse,json,hashlib,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'simulation/scripts/run'));import regression
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);out=src/'cancel_checks';out.mkdir(exist_ok=True)
 g=json.loads((src/'generation.json').read_text());original=src/'checks/soc_tb.v';tb=out/'soc_tb.v'
 monitor='''
 integer cancel_seen=0,cancel_checked=0,from_side=0,slow_side=0;
 reg[2:0] cancel_tag;reg cancel_now;
 always @(posedge clk) if(rst_n) begin
  if(dut.cpu.ex_fire && dut.cpu.ex_packet[203:200]==1 && dut.cpu.ex_side[223] && !dut.cpu.side_execute) cancel_seen=cancel_seen+1;
  if(dut.cpu.pair_issue && ((dut.cpu.dep_c && dut.cpu.tag_c[0]) || (dut.cpu.dep_d && dut.cpu.tag_d[0]))) from_side=from_side+1;
  if(dut.cpu.pair_issue && ((dut.cpu.dep_c && dut.cpu.destination[dut.cpu.tag_c[3:1]]!=0) || (dut.cpu.dep_d && dut.cpu.destination[dut.cpu.tag_d[3:1]]!=0))) slow_side=slow_side+1;
  cancel_now=dut.cpu.branch_redirect;cancel_tag=dut.cpu.redirect_tag;
  #1;
  if(cancel_now) begin cancel_checked=cancel_checked+1;if(dut.cpu.destination1[cancel_tag]!=0) $fatal(1,"Annulled branch-side producer remained live");end
 end
 always @(negedge clk) if(finish_count==1) $display("CANCEL_PASS annulled=%0d checked=%0d lane1_sources=%0d older_sources=%0d",cancel_seen,cancel_checked,from_side,slow_side);
'''
 tb.write_text(original.read_text().replace('endmodule',monitor+'\nendmodule'))
 files=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[]);files=[src/p.name if str(p.relative_to(ROOT)) in g['override_sha256'] else p for p in files]+[src/'pango_ram_wide_models.v']
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe');inputs=[*files,original,tb,Path(__file__).resolve()]
 def run(cmd,log):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=90);(out/log).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(log,p.stdout[-2000:]);return p.stdout.decode(errors='replace')
 run([iv,'-g2012','-s','soc_tb','-o',out/'sim.vvp',*files,tb],'compile.log');tests=[];coverage=[]
 for name in ['random_17','random_91','random_2026','prediction']:
  image=ROOT/f'simulation/results/{name}.hex';binary=image.with_suffix('.bin');inputs +=[image,binary];trace=out/(name+'.trace')
  s=run([vvp,out/'sim.vvp',f'+image={image}',f'+trace={trace}',f'+uart={out}/unused_uart.txt'],name+'.log');assert 'PASS cycles=' in s;regression.differential(binary.read_bytes(),trace)
  m=re.search(r'CANCEL_PASS ([^\r\n]+)',s);assert m;c={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])};coverage.append(dict(program=name,**c));tests.append(name+' PASS')
 assert sum(x['annulled'] for x in coverage)>0,coverage
 x=dict(status='PASS',tests=tests,coverage=coverage,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs})
 (out/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(coverage,indent=2))
if __name__=='__main__':main()
