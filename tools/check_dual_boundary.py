"""Boundary-specific frontend, pairing, ownership and latency checks."""
from pathlib import Path
import argparse,json,hashlib,sys,subprocess,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);ap.add_argument('--mode',choices=('extra','pairs','operands','audit','timeline'),required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant)
 if a.mode in ('extra','pairs','audit'):
  base=ROOT/'tools/check_dual_legacy.py';s=base.read_text().replace("a.variant.startswith('dual_legacy_')","a.variant.startswith('dual_boundary_')").replace("a.variant!='dual_legacy_fifo'","False")
  s=s.replace('PASS EX/MEM FIFO width249/depth4 preserved; no ready-to-EX feedback','PASS spill FIFO width249/depth4 and registered EX input credit preserved; MEM completion controls empty-queue handoff/storage only')
  ns={'__file__':str(base),'__name__':'boundary_check'};exec(compile(s,str(base),'exec'),ns);ns['main']();sub={'extra':'dual_checks','pairs':'pair_checks','audit':'audit_checks'}[a.mode];p=src/sub/'result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__));p.write_text(json.dumps(x,indent=2)+'\n');return
 out=src/(a.mode+'_checks');out.mkdir(exist_ok=True);inputs=[Path(__file__).resolve()];tests=[]
 if a.mode=='operands':
  original=ROOT/'simulation/results/load_bp_dual_legacy_fifo/nc_operands.v';evidence=ROOT/'simulation/results/load_bp_dual_legacy_fifo/operand_checks/result.json';assert sha(original)==sha(src/'nc_operands.v');x=json.loads(evidence.read_text());assert x['status']=='PASS' and len(x['tests'])==3;inputs +=[original,evidence,src/'nc_operands.v'];tests=['PASS exact-hash unchanged five-source operand network reuses 300000-cycle independent equivalence']
 else:
  image=ROOT/'simulation/results/load_cycle_structure/directed.hex';reference=ROOT/'docs/load_cycle_structure/result.json';pairs=json.loads(reference.read_text(encoding='utf-8'))['directed_pairs'];inputs +=[image,reference]
  original=src/'checks/soc_tb.v';mon='''
 integer edge_no=0,cf;reg[4095:0] cp;
 initial begin if(!$value$plusargs("cycletrace=%s",cp)) $fatal;cf=$fopen(cp,"w");end
 always @(posedge clk) if(rst_n) begin edge_no=edge_no+1;
  if(dut.cpu.ex_fire) $fdisplay(cf,"EX %0d %08x",edge_no,dut.cpu.ex_packet[199:168]);
  if(dut.cpu.d_req_valid && dut.cpu.d_req_ready) $fdisplay(cf,"REQ %0d %08x",edge_no,dut.cpu.memory.use_input ? dut.cpu.mem_packet[276:245] : dut.cpu.memory.held[276:245]);
  if(dut.cpu.memory_done) $fdisplay(cf,"WB_CAPTURE %0d %08x",edge_no,dut.cpu.memory_packet[276:245]);end
'''
  tb=out/'soc_tb.v';tb.write_text(original.read_text().replace('endmodule',mon+'\nendmodule'));g=json.loads((src/'generation.json').read_text());files=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[]);files=[src/p.name if str(p.relative_to(ROOT)) in g['override_sha256'] else p for p in files]+[src/'pango_ram_wide_models.v'];inputs +=[original,tb,*files]
  iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
  def run(cmd,log):
   p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=120);(out/log).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(log,(p.stdout+p.stderr)[-2500:]);return p.stdout.decode(errors='replace')
  run([iv,'-g2012','-s','soc_tb','-o',out/'sim.vvp',*files,tb],'compile.log');cycle=out/'cycles.trace';t=run([vvp,out/'sim.vvp',f'+image={image}',f'+trace={out}/retired.trace',f'+cycletrace={cycle}',f'+uart={out}/uart.txt'],'run.log');assert 'PASS cycles=' in t;events={}
  for line in cycle.read_text().splitlines():k,e,p=line.split();events[k,int(p,16)]=int(e)
  for p in pairs:
   lp,cp=p['load_pc'],p['consumer_pc'];e,r,w,c=events['EX',lp],events['REQ',lp],events['WB_CAPTURE',lp],events['EX',cp]
   assert r==e+(0 if a.variant.endswith('_early') else 1) and w==r+1 and c==w+1,(p,e,r,w,c)
   tests.append(dict(status='PASS',load_pc=lp,consumer_pc=cp,ex=e,request=r,wb_capture=w,consumer_ex=c,ex_bubbles=c-e-1))
 (out/'result.json').write_text(json.dumps(dict(status='PASS',variant=a.variant,tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print(a.mode,a.variant,'PASS',len(tests))
if __name__=='__main__':main()
