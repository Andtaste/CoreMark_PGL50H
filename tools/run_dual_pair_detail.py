"""Per-type unpaired census, with full decoder sources and youngest live tags."""
from pathlib import Path
import hashlib,json,re,sys
import research_dual_issue as trial
ROOT=Path(__file__).resolve().parents[1]
MON=r'''
 integer pd_count[0:6],pd_raw[0:6],pd_waw[0:6],pd_res[0:6],pd_clean[0:6],pd_ready[0:6];integer pd_i,pd_type;
 integer pd_aluload=0,pd_alustore=0,pd_aluload_ready=0,pd_alustore_ready=0;
 function pd_source_ready;input[4:0] rs;input used;integer age,idx;reg found;reg[3:0] tag;begin
  found=0;tag=0;
  for(age=0;age<8;age=age+1)begin idx=(CPU.tail+age)%8;if(CPU.live[idx])begin
   if(CPU.destination[idx]==rs && rs!=0)begin found=1;tag={idx[2:0],1'b0};end
   if(CPU.destination1[idx]==rs && rs!=0)begin found=1;tag={idx[2:0],1'b1};end
  end end
  pd_source_ready=!used || rs==0 || !found ||
   (CPU.f_valid && tag=={CPU.f_tag,1'b0}) || (CPU.f1_valid && tag=={CPU.f_tag,1'b1}) ||
   (CPU.m_valid && tag=={CPU.m_tag,CPU.m_lane}) ||
   (CPU.commit && CPU.w_wr && CPU.w_rd!=0 && tag=={CPU.w_tag,1'b0}) ||
   (CPU.commit1 && CPU.w1_wr && CPU.w1_rd!=0 && tag=={CPU.w_tag,1'b1});
 end endfunction
 wire pd_r=CPU.id_wr && CPU.rd!=0 && ((CPU.id1_use1 && CPU.rd==CPU.rs1_1) || (CPU.id1_use2 && CPU.rd==CPU.rs2_1));
 wire pd_w=CPU.id_wr && CPU.id1_wr && CPU.rd!=0 && CPU.rd==CPU.rd1;
 wire pd_resource=((CPU.id_kind==4 || CPU.id_kind==5) && (CPU.id1_kind==4 || CPU.id1_kind==5)) || (CPU.id_kind==6 && !CPU.id_insn[14] && CPU.id1_kind==6 && !CPU.id_insn1[14]) || (CPU.id_kind>=1 && CPU.id_kind<=3 && CPU.id1_kind>=1 && CPU.id1_kind<=3);
 wire pd_both_ready=pd_source_ready(CPU.rs1,CPU.use1) && pd_source_ready(CPU.rs2,CPU.use2) && pd_source_ready(CPU.rs1_1,CPU.id1_use1) && pd_source_ready(CPU.rs2_1,CPU.id1_use2);
 wire pd_clean_pair=!CPU.id_fault && !CPU.id_illegal && !CPU.id1_illegal && !pd_r && !pd_w && !pd_resource;
 always @(posedge clk) if(rst_n) begin
  if(CPU.csr.stats.control && CPU.csr.stats.control_data[1])begin
   for(pd_i=0;pd_i<7;pd_i=pd_i+1)begin pd_count[pd_i]=0;pd_raw[pd_i]=0;pd_waw[pd_i]=0;pd_res[pd_i]=0;pd_clean[pd_i]=0;pd_ready[pd_i]=0;end
   pd_aluload=0;pd_alustore=0;pd_aluload_ready=0;pd_alustore_ready=0;
  end else if(!CPU.csr.stats.control && CPU.csr.stats.enabled && CPU.issue && CPU.id_second && !CPU.pair_issue)begin
   case(CPU.id1_kind)0:pd_type=0;1:pd_type=1;6:pd_type=CPU.id_insn1[14] ? 6 : 2;4:pd_type=3;5:pd_type=4;2,3:pd_type=5;default:pd_type=6;endcase
   pd_count[pd_type]=pd_count[pd_type]+1;if(pd_r)pd_raw[pd_type]=pd_raw[pd_type]+1;if(pd_w)pd_waw[pd_type]=pd_waw[pd_type]+1;if(pd_resource)pd_res[pd_type]=pd_res[pd_type]+1;
   if(pd_clean_pair)begin
    pd_clean[pd_type]=pd_clean[pd_type]+1;if(pd_both_ready)pd_ready[pd_type]=pd_ready[pd_type]+1;
    if(CPU.id_kind==0 && !CPU.id_prediction[31] && !CPU.id_prediction1[31])begin
     if(CPU.id1_kind==4)begin pd_aluload=pd_aluload+1;if(pd_both_ready)pd_aluload_ready=pd_aluload_ready+1;end
     if(CPU.id1_kind==5)begin pd_alustore=pd_alustore+1;if(pd_both_ready)pd_alustore_ready=pd_alustore_ready+1;end
    end
   end
  end
 end
 always @(negedge clk)if(check_secondary)begin
  for(pd_i=0;pd_i<7;pd_i=pd_i+1)$display("PAIR_DETAIL type=%0d count=%0d raw=%0d waw=%0d resource=%0d clean=%0d ready=%0d",pd_i,pd_count[pd_i],pd_raw[pd_i],pd_waw[pd_i],pd_res[pd_i],pd_clean[pd_i],pd_ready[pd_i]);
  $display("PAIR_SINGLE_LSU alu_load=%0d alu_store=%0d alu_load_ready=%0d alu_store_ready=%0d",pd_aluload,pd_alustore,pd_aluload_ready,pd_alustore_ready);
 end
'''
def main():
 v=sys.argv[sys.argv.index('--variant')+1];phase=sys.argv[sys.argv.index('--phase')+1];prepare=trial.prepare_benches
 def benches(dest):
  result=prepare(dest)
  for p in result:p.write_text(p.read_text().replace('endmodule',MON.replace('CPU','dut.cpu' if p.name=='soc_tb.v' else 'dut')+'\nendmodule'))
  return result
 trial.prepare_benches=benches;base=ROOT/'tools/run_dual_mul_tail_v2.py';ns={'__file__':str(base),'__name__':'pair_detail'};exec(compile(base.read_text(),str(base),'exec'),ns);ns['main']();src=ROOT/('simulation/results/load_bp_'+v)
 for p in [src/phase/'result.json']+([src/'result.json'] if phase=='performance' else []):
  x=json.loads(p.read_text());t=(src/phase/'simulation.log').read_text(errors='replace');rows=[{k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m)} for m in re.findall(r'^PAIR_DETAIL ([^\r\n]+)',t,re.M)];assert len(rows)==7
  assert sum(z['count'] for z in rows)==x['pair_reject']['groups']-x['pair_reject']['paired']-x['pair_reject']['no_second'];x['pair_detail']=rows;m=re.search(r'^PAIR_SINGLE_LSU ([^\r\n]+)',t,re.M);assert m;x['pair_single_lsu']={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])};x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
 print('Detailed pair census PASS')
if __name__=='__main__':main()
