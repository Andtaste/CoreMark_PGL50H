"""Verify actual ID splitting/capture against producer classes and queue state."""
from pathlib import Path
import argparse,json,hashlib,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'simulation/scripts/run'));import regression
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);out=src/'policy_checks';out.mkdir(exist_ok=True)
 g=json.loads((src/'generation.json').read_text());files=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[]);files=[src/p.name if str(p.relative_to(ROOT)) in g['override_sha256'] else p for p in files]+[src/'pango_ram_wide_models.v']
 original=src/'checks/soc_tb.v';tb=out/'soc_tb.v';block='''
 reg[3:0] pk_main[0:7],pk_side[0:7];reg p_push,p_slot;integer p_pairs=0,p_split=0,p_dep=0,pi;reg[3:0] pt;
 always @(posedge clk) if(rst_n) begin
  p_push=dut.cpu.pair_issue;p_slot=dut.cpu.operands.wr;
  if(dut.cpu.issue) begin pk_main[dut.cpu.tail]<=dut.cpu.id_kind;pk_side[dut.cpu.tail]<=dut.cpu.id_side_kind;if(dut.cpu.second_dep) p_split=p_split+1;end
  if(p_push) begin
   p_pairs=p_pairs+1;if(dut.cpu.dep_c || dut.cpu.dep_d) p_dep=p_dep+1;
   for(pi=0;pi<2;pi=pi+1) if(pi==0 ? dut.cpu.dep_c : dut.cpu.dep_d) begin
    pt=pi==0 ? dut.cpu.tag_c : dut.cpu.tag_d;
    POLICY
   end
  end
  #1;
  POST
 end
 always @(negedge clk) if(finish_count==1) $display("POLICY_PASS pairs=%0d split=%0d dependent_pairs=%0d",p_pairs,p_split,p_dep);
'''
 if a.variant.endswith('ready'):
  policy='if(!((dut.cpu.f_valid && pt=={dut.cpu.f_tag,1\'b0}) || (dut.cpu.f1_valid && pt=={dut.cpu.f1_tag,1\'b1}) || (dut.cpu.m_valid && pt=={dut.cpu.m_tag,dut.cpu.m_lane}) || (dut.cpu.commit && dut.cpu.w_wr && dut.cpu.w_rd!=0 && pt=={dut.cpu.w_tag,1\'b0}) || (dut.cpu.commit1 && dut.cpu.w1_rd!=0 && pt=={dut.cpu.w_tag,1\'b1}))) $fatal(1,"Unready secondary admitted");'
  post='if(p_push && (dut.cpu.operands.wc[p_slot] || dut.cpu.operands.wd[p_slot])) $fatal(1,"Ready-only source not captured on insertion");'
 else:
  policy='if((pt[0] ? pk_side[pt[3:1]] : pk_main[pt[3:1]])==4 || (pt[0] ? pk_side[pt[3:1]] : pk_main[pt[3:1]])==6) $fatal(1,"Slow producer admitted");';post=''
 tb.write_text(original.read_text().replace('endmodule',block.replace('POLICY\n',policy+'\n').replace('  POST','  '+post)+'\nendmodule'))
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe');inputs=[*files,original,tb,Path(__file__).resolve()]
 def run(cmd,log):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=90);(out/log).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(log,p.stdout[-2000:]);return p.stdout.decode(errors='replace')
 run([iv,'-g2012','-s','soc_tb','-o',out/'sim.vvp',*files,tb],'compile.log');tests=[];coverage=[]
 for name in ['random_17','random_91','random_2026','prediction']:
  image=ROOT/f'simulation/results/{name}.hex';binary=image.with_suffix('.bin');inputs +=[image,binary];trace=out/(name+'.trace')
  s=run([vvp,out/'sim.vvp',f'+image={image}',f'+trace={trace}',f'+uart={out}/unused_uart.txt'],name+'.log');assert 'PASS cycles=' in s;regression.differential(binary.read_bytes(),trace)
  m=re.search(r'POLICY_PASS ([^\r\n]+)',s);assert m;c={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])};coverage.append(dict(program=name,**c));tests.append(name+' PASS')
 assert sum(c['split'] for c in coverage)>0 and sum(c['dependent_pairs'] for c in coverage)>0
 x=dict(status='PASS',tests=tests,coverage=coverage,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs});(out/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(coverage,indent=2))
if __name__=='__main__':main()
