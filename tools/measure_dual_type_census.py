"""Repeat identical RTL/image with bench-only issued/retired side instruction census."""
from pathlib import Path
import json,sys,shutil,re
import research_dual_issue as t
def main():
 variant=sys.argv[sys.argv.index('--variant')+1];sys.argv=[sys.argv[0],'--phase','performance']
 src=t.ROOT/('simulation/results/load_bp_'+variant);out=t.ROOT/'simulation/results/dual_type_census'/variant;out.mkdir(parents=True,exist_ok=True)
 g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert t.sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v');(out/'generation.json').write_text(json.dumps(g,indent=2)+'\n')
 t.OUT=out;parents=[]
 def benches(dest):
  paths=[]
  for name,cpu in (('core_tb','dut'),('soc_tb','dut.cpu')):
   p=src/'performance'/(name+'.v');parents.append(p);s=p.read_text()
   block=r'''
 integer cs_alu=0,cs_branch=0,cs_mul=0,ci_alu=0,ci_branch=0,ci_mul=0,ci_cross=0,ci_pop2=0;
 always @(posedge clk) if(rst_n) begin
  if(CPU.csr.stats.control && CPU.csr.stats.control_data[1]) begin
   cs_alu=0;cs_branch=0;cs_mul=0;ci_alu=0;ci_branch=0;ci_mul=0;ci_cross=0;ci_pop2=0;
  end else if(!CPU.csr.stats.control && CPU.csr.stats.enabled) begin
   if(CPU.commit1) begin
    if(CPU.w1_insn[6:0]==7'h63) cs_branch=cs_branch+1;
    else if(CPU.w1_insn[6:0]==7'h33 && CPU.w1_insn[31:25]==1) cs_mul=cs_mul+1;
    else cs_alu=cs_alu+1;
   end
   if(CPU.pair_issue) begin
    if(CPU.id1_kind==1) ci_branch=ci_branch+1;
    else if(CPU.id1_kind==6) ci_mul=ci_mul+1;
    else ci_alu=ci_alu+1;
    CROSS
   end
   POP2
  end
 end
 always @(negedge clk) if(check_secondary) begin
  if(cs_alu+cs_branch+cs_mul!=ref_secondary || ci_alu+ci_branch+ci_mul!=win_pairs) $fatal(1,"Side census/reference mismatch");
  $display("CENSUS_WINDOW retired_alu=%0d retired_branch=%0d retired_mul=%0d issued_alu=%0d issued_branch=%0d issued_mul=%0d cross_pairs=%0d pop_two_groups=%0d",cs_alu,cs_branch,cs_mul,ci_alu,ci_branch,ci_mul,ci_cross,ci_pop2);
 end
'''
   block=block.replace('CROSS','if(CPU.fetch.cross_window) ci_cross=ci_cross+1;' if 'slide' in variant else '').replace('POP2','if(CPU.fetch.pop_two_groups) ci_pop2=ci_pop2+1;' if 'slide' in variant else '')
   q=dest/(name+'.v');q.write_text(s.replace('endmodule',block.replace('CPU',cpu)+'\nendmodule'));paths.append(q)
  return tuple(paths)
 t.prepare_benches=benches;original=t.subprocess.run;model=t.ROOT/'simulation/models/pango_ram_models.v';replacement=out/'pango_ram_wide_models.v'
 def run(cmd,*args,**kwargs):
  cmd=[str(replacement) if str(p)==str(model) else t.linux(replacement) if str(p)==t.linux(model) else p for p in cmd];return original(cmd,*args,**kwargs)
 t.subprocess.run=run;t.main()
 p=out/'performance/result.json';x=json.loads(p.read_text());ref=json.loads((src/'performance/result.json').read_text())
 for k in ('metrics','dual','predictor','multiply'):assert x[k]==ref[k],(variant,k)
 s=(out/'performance/simulation.log').read_text(errors='replace');m=re.search(r'CENSUS_WINDOW ([^\r\n]+)',s);assert m
 x['census']={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])};x['variant']=variant;x['parent_profile_identical']=True
 for k in ('input_sha256','actual_compile_sha256'):
  x[k].pop(str(model.relative_to(t.ROOT)),None);x[k][str(replacement.relative_to(t.ROOT))]=t.sha(replacement)
 x['input_sha256'].update({str(p.relative_to(t.ROOT)):t.sha(p) for p in parents+[Path(__file__).resolve()]});t.save(out/'census.json',x);print('CENSUS',variant,x['census'])
if __name__=='__main__':main()
