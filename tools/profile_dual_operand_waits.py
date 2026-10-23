"""Classify operand waits by observed per-lane producer type, without RTL edits."""
from pathlib import Path
import hashlib,json,re,subprocess
from profile_btb_hashes import linux
ROOT=Path(__file__).resolve().parents[1]
NAMES='cycles operand_wait only_load only_mul load_mul other_mix any_load any_mul any_alu any_link any_other alu_already_executed primary_only side_only both missing_a missing_b missing_c missing_d'.split()
BLOCK=r'''
 integer wp[0:18];integer producer_kind[0:15];reg[15:0] producer_done=0;
 integer wi;reg wl,wm,wa0,wj,wo,wdone,primary_missing,side_missing;
 initial begin for(wi=0;wi<19;wi=wi+1) wp[wi]=0;for(wi=0;wi<16;wi=wi+1)producer_kind[wi]=-1;end
 task classify_wait(input[3:0] token);
  begin
   case(producer_kind[token])
    4:wl=1;
    6:wm=1;
    0:begin wa0=1;if(producer_done[token]) wdone=1;end
    2,3:wj=1;
    default:wo=1;
   endcase
  end
 endtask
 always @(posedge clk) if(rst_n) begin
  if(dut.cpu.csr.stats.control && dut.cpu.csr.stats.control_data[1]) begin
   for(wi=0;wi<19;wi=wi+1) wp[wi]=0;
  end else if(!dut.cpu.csr.stats.control && dut.cpu.csr.stats.enabled) begin
   wp[0]=wp[0]+1;
   if(dut.cpu.ex_occupied && !dut.cpu.ex_valid) begin
    wp[1]=wp[1]+1;wl=0;wm=0;wa0=0;wj=0;wo=0;wdone=0;primary_missing=0;side_missing=0;
    if(!dut.cpu.operands.available_a[dut.cpu.operands.rd]) begin
     classify_wait(dut.cpu.operands.dep_a[dut.cpu.operands.rd]);primary_missing=1;wp[15]=wp[15]+1;end
    if(!dut.cpu.operands.available_b[dut.cpu.operands.rd]) begin
     classify_wait(dut.cpu.operands.dep_b[dut.cpu.operands.rd]);primary_missing=1;wp[16]=wp[16]+1;end
    if(!dut.cpu.operands.available_c[dut.cpu.operands.rd]) begin
     classify_wait(dut.cpu.operands.dep_c[dut.cpu.operands.rd]);side_missing=1;wp[17]=wp[17]+1;end
    if(!dut.cpu.operands.available_d[dut.cpu.operands.rd]) begin
     classify_wait(dut.cpu.operands.dep_d[dut.cpu.operands.rd]);side_missing=1;wp[18]=wp[18]+1;end
    if(wl && !wm && !wa0 && !wj && !wo)wp[2]=wp[2]+1;
    else if(wm && !wl && !wa0 && !wj && !wo)wp[3]=wp[3]+1;
    else if(wl && wm && !wa0 && !wj && !wo)wp[4]=wp[4]+1;
    else wp[5]=wp[5]+1;
    if(wl)wp[6]=wp[6]+1;if(wm)wp[7]=wp[7]+1;if(wa0)wp[8]=wp[8]+1;
    if(wj)wp[9]=wp[9]+1;if(wo)wp[10]=wp[10]+1;if(wdone)wp[11]=wp[11]+1;
    if(primary_missing && side_missing)wp[14]=wp[14]+1;
    else if(primary_missing)wp[12]=wp[12]+1;
    else if(side_missing)wp[13]=wp[13]+1;
    else $fatal(1,"Unclassified operand wait");
   end
  end
  if(dut.cpu.ex_fire) begin
   if(dut.cpu.execute_packet[7:4]==0)producer_done[{dut.cpu.ex_tag,1'b0}]=1;
   if(dut.cpu.ex_side[223] && dut.cpu.ex_side[203:200]==0)producer_done[{dut.cpu.ex_tag,1'b1}]=1;
  end
  if(dut.cpu.issue) begin
   producer_kind[{dut.cpu.tail,1'b0}]=(dut.cpu.id_kind==6 && dut.cpu.id_insn[14]) ? 7 : int'(dut.cpu.id_kind);
   producer_kind[{dut.cpu.tail,1'b1}]=int'(dut.cpu.id_side_kind);
   producer_done[{dut.cpu.tail,1'b0}]=0;producer_done[{dut.cpu.tail,1'b1}]=0;
  end
 end
 always @(negedge clk) if(check_stats)for(wi=0;wi<19;wi=wi+1)$display("OPERAND_WAIT_PROFILE %0d %0d",wi,wp[wi]);
'''

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 m=json.loads((ROOT/'docs/active_optimization_baseline.json').read_text());src=ROOT/m['project_directory']
 for n,h in m['input_sha256'].items():assert sha(src/n)==h,n
 out=ROOT/f"simulation/results/autonomous_20261022/operand_wait_profile_{m['source_trial']}";assert not out.exists();out.mkdir()
 sim=ROOT/f"simulation/results/load_bp_dual_boundary_auto_{m['source_trial']}"
 bench=out/'soc_tb.v';bench.write_text((sim/'performance/soc_tb.v').read_text().replace('endmodule',BLOCK+'\nendmodule'))
 files=sorted((src/'source/core').glob('*.v'))+[sim/'performance/nc_uart_sim.v',src/'source/sys_bus/nc_local_bus.v',src/'source/top/nc_soc.v',sim/'pango_ram_wide_models.v',bench]
 prefix=['wsl.exe','-d','Ubuntu','--cd',linux(out),'--']
 def run(args,name):
  with (out/name).open('wb') as log:subprocess.run([*prefix,*args],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
 run(['verilator','--binary','--timing','-j','4','-Wno-fatal','-DCOREMARK_SIM','--top-module','soc_tb','--Mdir',linux(out/'obj'),*[linux(f) for f in files]],'compile.log')
 image=ROOT/'sw/build/coremark_performance_10/coremark.hex'
 run([linux(out/'obj/Vsoc_tb'),f'+image={linux(image)}',f'+uart={linux(out)}/uart.txt',f'+trace={linux(out)}/unused.trace','+notrace=1','+limit=33000000'],'simulation.log')
 log=(out/'simulation.log').read_text(errors='replace');uart=(out/'uart.txt').read_text(errors='replace')
 assert 'COUNTER_CHECK_PASS' in log and 'CRC validation   : PASS' in uart
 metrics={s.split(':',1)[0].strip():s.split(':',1)[1].strip() for s in uart.splitlines() if ':' in s}
 assert int(metrics['Benchmark cycles64'])==m['benchmark_cycles']
 counts={NAMES[int(i)]:int(v) for i,v in re.findall(r'OPERAND_WAIT_PROFILE (\d+) (\d+)',log)}
 assert len(counts)==19 and counts['cycles']==m['stats_cycles']
 assert counts['operand_wait']==int(metrics['EX operand wait'].split()[0])
 assert sum(counts[k] for k in NAMES[2:6])==counts['operand_wait']
 assert sum(counts[k] for k in NAMES[12:15])==counts['operand_wait']
 (out/'result.json').write_text(json.dumps(dict(status='PASS',baseline=m['variant'],counts=counts,scope='Read-only per-lane producer observer; any_* classes overlap, counts are not guaranteed recoverable cycles',input_sha256={str(p.relative_to(ROOT)):sha(p) for p in files+[image,Path(__file__).resolve()]}),indent=2)+'\n')
 print(json.dumps(counts,indent=2))

if __name__=='__main__':main()
