"""Read-only mutually exclusive issue-time reasons for not pairing."""
from pathlib import Path
import json,shutil,sys,re
import research_dual_issue as trial
def main():
 src=trial.ROOT/'simulation/results/load_bp_dual_issue_predecode';dest=src.with_name('load_bp_dual_issue_profile');dest.mkdir(exist_ok=True)
 meta=json.loads((src/'generation.json').read_text())
 for n,h in meta['override_sha256'].items():
  p=src/Path(n).name;assert trial.sha(p)==h,n;shutil.copyfile(p,dest/p.name)
 shutil.copyfile(src/'generation.json',dest/'generation.json')
 original=trial.prepare_benches
 def prepare(out):
  core,soc=original(out);s=soc.read_text();observer='''
 integer no_second=0,primary_class=0,prediction_mask=0,secondary_class=0,pair_raw=0,pair_waw=0,older_dependency=0,paired=0,groups=0;
 always @(posedge clk) if(rst_n && dut.cpu.csr.stats.enabled && !dut.cpu.csr.stats.control && dut.cpu.issue) begin
  groups=groups+1;
  if(!dut.cpu.id_second) no_second=no_second+1;
  else if(dut.cpu.id_fault || !dut.cpu.id_pair_flags[4]) primary_class=primary_class+1;
  else if(dut.cpu.id_prediction[30] || dut.cpu.id_prediction1[31]) prediction_mask=prediction_mask+1;
  else if(!dut.cpu.id_pair_flags[8]) secondary_class=secondary_class+1;
  else if(dut.cpu.id_pair_flags[2] && dut.cpu.rd!=0 &&
    ((dut.cpu.id_pair_flags[5] && dut.cpu.rd==dut.cpu.rs1_1) ||
     (dut.cpu.id_pair_flags[6] && dut.cpu.rd==dut.cpu.rs2_1))) pair_raw=pair_raw+1;
  else if(dut.cpu.id_pair_flags[2] && dut.cpu.rd!=0 && dut.cpu.rd==dut.cpu.rd1) pair_waw=pair_waw+1;
  else if(dut.cpu.second_dep) older_dependency=older_dependency+1;
  else begin
   if(!dut.cpu.pair_issue) $fatal(1,"Pair partition does not match hardware");
   paired=paired+1;
  end
 end
 always @(negedge clk) if(check_secondary) begin
  if(no_second+primary_class+prediction_mask+secondary_class+pair_raw+pair_waw+older_dependency+paired!=groups || paired!=win_pairs || groups!=win_issued) $fatal(1,"Issue reason partition mismatch");
  $display("PAIR_REASONS groups=%0d no_second=%0d primary_class=%0d prediction_mask=%0d secondary_class=%0d pair_raw=%0d pair_waw=%0d older_dependency=%0d paired=%0d",groups,no_second,primary_class,prediction_mask,secondary_class,pair_raw,pair_waw,older_dependency,paired);
 end
'''
  s=s.replace('endmodule',observer+'\nendmodule');soc.write_text(s);return core,soc
 trial.OUT=dest;trial.prepare_benches=prepare;sys.argv=[sys.argv[0],'--phase','performance'];trial.main()
 log=(dest/'performance/simulation.log').read_text(errors='replace');m=re.search(r'PAIR_REASONS ([^\r\n]+)',log);assert m
 reasons={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])}
 for p in (dest/'result.json',dest/'performance/result.json'):
  x=json.loads(p.read_text());reference=json.loads((src/'result.json').read_text())
  for key in ('metrics','predictor','multiply','dual'):assert x[key]==reference[key],key
  x['variant']='dual_issue_profile';x['scope']='Observation only; same candidate RTL; issued groups include wrong paths';x['pair_reasons']=reasons
  x['input_sha256']['tools/profile_dual_issue.py']=trial.sha(Path(__file__))
  trial.save(p,x)
 print(json.dumps(reasons,indent=2))
if __name__=='__main__':main()
