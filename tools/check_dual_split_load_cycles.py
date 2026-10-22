"""Observe real current load EX/request/WB/consumer edges; no early-return RTL."""
from pathlib import Path
import json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'simulation/results/dual_split_load_cycles'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 OUT.mkdir(exist_ok=True);image=ROOT/'simulation/results/load_cycle_structure/directed.hex';reference=ROOT/'docs/load_cycle_structure/result.json';pairs=json.loads(reference.read_text(encoding='utf-8'))['directed_pairs'];results={};inputs=[image,reference,Path(__file__).resolve()]
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
 for variant in ['dual_joint_fix','dual_split_ready','dual_split_slow']:
  src=ROOT/('simulation/results/load_bp_'+variant);out=OUT/variant;out.mkdir(exist_ok=True);g=json.loads((src/'generation.json').read_text());bench=src/'checks/soc_tb.v';s=bench.read_text()
  monitor='''
 integer lc_edge=0,lc_fd;reg[4095:0] lc_file;
 initial begin if(!$value$plusargs("cycletrace=%s",lc_file)) $fatal(1,"Need cycletrace");lc_fd=$fopen(lc_file,"w");end
 always @(posedge clk) if(rst_n) begin
  lc_edge=lc_edge+1;
  if(dut.cpu.ex_fire) $fdisplay(lc_fd,"EX %0d %08x",lc_edge,dut.cpu.ex_packet[199:168]);
  if(dut.cpu.d_req_valid && dut.cpu.d_req_ready) $fdisplay(lc_fd,"REQ %0d %08x",lc_edge,dut.cpu.mem_packet[276:245]);
  if(dut.cpu.memory_done) $fdisplay(lc_fd,"WB_CAPTURE %0d %08x",lc_edge,dut.cpu.memory_packet[276:245]);
 end
'''
  tb=out/'soc_tb.v';tb.write_text(s.replace('endmodule',monitor+'\nendmodule'));files=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[]);files=[src/p.name if str(p.relative_to(ROOT)) in g['override_sha256'] else p for p in files]+[src/'pango_ram_wide_models.v'];inputs +=[*files,bench,tb]
  def run(cmd,log):
   p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=90);(out/log).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(log,p.stdout[-2000:]);return p.stdout.decode(errors='replace')
  run([iv,'-g2012','-s','soc_tb','-o',out/'sim.vvp',*files,tb],'compile.log');trace=out/'retired.trace';cycle=out/'cycles.trace';s=run([vvp,out/'sim.vvp',f'+image={image}',f'+trace={trace}',f'+cycletrace={cycle}',f'+uart={out}/unused.txt'],'run.log');assert 'PASS cycles=' in s
  events={}
  for line in cycle.read_text().splitlines():kind,edge,pc=line.split();events[kind,int(pc,16)]=int(edge)
  measured=[]
  for p in pairs:
   lp,cp=p['load_pc'],p['consumer_pc'];e=events['EX',lp];r=events['REQ',lp];w=events['WB_CAPTURE',lp];c=events['EX',cp]
   assert r>=e+1 and w==r+1 and c==w+1,(variant,p,e,r,w,c)
   measured.append(dict(load_pc=lp,consumer_pc=cp,ex=e,request=r,wb_capture=w,consumer_ex=c,ex_bubbles=c-e-1))
  results[variant]=measured
 for variant in ['dual_split_ready','dual_split_slow']:
  assert (OUT/variant/'retired.trace').read_text()==(OUT/'dual_joint_fix/retired.trace').read_text(),variant
 x=dict(status='PASS',scope='Read-only current full SoC timeline; no early-start/return implementation',directed=results,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs})
 (OUT/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(results,indent=2))
if __name__=='__main__':main()
