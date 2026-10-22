"""Independent six-source reference and future-identity protocol checks."""
from pathlib import Path
import argparse,json,hashlib,subprocess,sys,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=('audit','operands','protocol'),required=True);a=ap.parse_args();src=ROOT/'simulation/results/load_bp_dual_legacy_select';out=src/(a.mode+'_checks');out.mkdir(exist_ok=True);inputs=[Path(__file__).resolve()]
 if a.mode=='audit':
  base=ROOT/'tools/check_dual_legacy.py';s=base.read_text().replace("assert 'rsp_valid && !rsp_error && !kill && !exception && kind==4 && wr && rd!=0' in mem","assert 'rsp_valid && !rsp_error && !kill && !exception && kind==4 && load_word && wr && rd!=0' in mem and 'return_data=rsp_data' in mem")
  ns={'__file__':str(base),'__name__':'select_audit'};exec(compile(s,str(base),'exec'),ns);sys.argv=[str(base),'--variant','dual_legacy_select','--mode','audit'];ns['main']();p=out/'result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__));p.write_text(json.dumps(x,indent=2)+'\n');return
 iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
 def run(cmd,log):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(out/log).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(log,(p.stdout+p.stderr)[-2500:]);return p.stdout.decode(errors='replace')
 tests=[]
 if a.mode=='operands':
  parent=ROOT/'simulation/results/load_bp_dual_legacy_return/operands_checks';reference=parent/'reference.v';original=parent/'operands_tb.v';ref=out/'reference.v';ref.write_bytes(reference.read_bytes());s=original.read_text()
  s=s.replace('reg[2:0] next_f_tag=0,next_m_tag=0,next_w_tag=0;', 'reg[2:0] next_f_tag=0,next_w_tag=0,next_r_tag=0;reg[3:0] next_m_tag=0;')
  s=s.replace("m_tag<={next_m_tag,1'b0};", "m_tag<=next_m_tag;r_tag<={next_r_tag,1'b0};")
  s=s.replace('next_m_tag=rng[5:3]', 'next_m_tag=rng[6:3]').replace('next_m_tag=tag_a[3:1]', 'next_m_tag=tag_a')
  s=s.replace('r_tag=rng[4:1]', 'next_r_tag=rng[3:1]').replace('r_tag=tag_c', 'next_r_tag=tag_c[3:1]')
  idx=s.index(' old_nc_operands ref_dut');s=s[:idx].replace('.wait_a(wait_a)', '.next_f_tag(next_f_tag),.next_m_tag(next_m_tag),.next_w_tag(next_w_tag),.next_r_tag(next_r_tag),.wait_a(wait_a)')+s[idx:]
  tb=out/'operands_tb.v';tb.write_text(s);actual=src/'nc_operands.v';inputs +=[original,reference,ref,tb,actual]
  run([iv,'-g2012','-s','operands_equivalence_tb','-o',out/'sim.vvp',actual,ref,tb],'compile.log')
  for seed in (17,91,2026):
   t=run([vvp,out/'sim.vvp',f'+seed={seed}'],f'seed_{seed}.log');assert 'PASS operands equivalence cycles=100000' in t;tests.append(t.strip())
 else:
  g=json.loads((src/'generation.json').read_text());files=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[]);files=[src/p.name if str(p.relative_to(ROOT)) in g['override_sha256'] else p for p in files]+[src/'pango_ram_wide_models.v'];inputs+=files
  mon='''
 reg[2:0] pr,pf,pw;reg[3:0] pm;integer protocol_edges=0;
 always @(posedge clk) if(rst_n) begin
 pr=dut.cpu.r_next_tag;pf=dut.cpu.ex_tag;pw=dut.cpu.future_w_tag;pm=dut.cpu.m_next_tag;
 #1;protocol_edges=protocol_edges+1;
 if(dut.cpu.r_valid && dut.cpu.r_tag!=pr) $fatal(1,"Future R identity mismatch");
 if(dut.cpu.f_valid && dut.cpu.f_tag!=pf) $fatal(1,"Future F identity mismatch");
 if(dut.cpu.f1_valid && dut.cpu.f1_tag!=pf) $fatal(1,"Future F1 identity mismatch");
 if(dut.cpu.commit && dut.cpu.w_tag!=pw) $fatal(1,"Future W identity mismatch");
 if(dut.cpu.m_valid && {dut.cpu.m_tag,dut.cpu.m_lane}!=pm) $fatal(1,"Future M identity mismatch");
 end
 always @(negedge clk) if(finish_count==1) $display("PROTOCOL_PASS edges=%0d",protocol_edges);
'''
  original=src/'checks/soc_tb.v';tb=out/'soc_tb.v';tb.write_text(original.read_text().replace('endmodule',mon+'\nendmodule'));inputs +=[original,tb]
  run([iv,'-g2012','-s','soc_tb','-o',out/'sim.vvp',*files,tb],'compile.log')
  sys.path.insert(0,str(ROOT/'simulation/scripts/run'));import regression
  for name in ('random_17','random_91','random_2026','prediction','throughput'):
   image=ROOT/f'simulation/results/{name}.hex';binary=image.with_suffix('.bin');trace=out/(name+'.trace');inputs +=[image,binary]
   t=run([vvp,out/'sim.vvp',f'+image={image}',f'+trace={trace}',f'+uart={out}/unused.txt'],name+'.log');assert 'PASS cycles=' in t and 'PROTOCOL_PASS' in t;regression.differential(binary.read_bytes(),trace);tests.append(name+' PASS')
 x=dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs});(out/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(a.mode,'PASS',len(tests))
if __name__=='__main__':main()
