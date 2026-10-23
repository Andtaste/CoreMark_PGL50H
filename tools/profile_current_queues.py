"""Observe registered-credit queue stalls without changing RTL or firmware."""
from pathlib import Path
import hashlib,json,re,subprocess
from profile_btb_hashes import linux
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'simulation/results/autonomous_20261022/queue_profile'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 m=json.loads((ROOT/'docs/active_optimization_baseline.json').read_text());src=ROOT/m['project_directory']
 for n,h in m['input_sha256'].items():assert sha(src/n)==h,n
 sim=ROOT/f"simulation/results/load_bp_dual_boundary_auto_{m['source_trial']}";OUT.mkdir(exist_ok=True)
 bench=OUT/'soc_tb.v';s=(sim/'performance/soc_tb.v').read_text()
 block='''
 integer qp[0:9];integer qi;
 initial for(qi=0;qi<10;qi=qi+1) qp[qi]=0;
 always @(posedge clk) if(rst_n) begin
  if(dut.cpu.csr.stats.control && dut.cpu.csr.stats.control_data[1])
   for(qi=0;qi<10;qi=qi+1) qp[qi]=0;
  else if(!dut.cpu.csr.stats.control && dut.cpu.csr.stats.enabled) begin
   qp[0]=qp[0]+1;
   if(dut.cpu.id_valid && !dut.cpu.ex_credit && dut.cpu.ex_pop && !dut.cpu.redirect && !dut.cpu.do_trap) qp[1]=qp[1]+1;
   if(dut.cpu.execute_valid && !dut.cpu.mem_credit && dut.cpu.mem_valid && dut.cpu.memory_ready && !dut.cpu.redirect && !dut.cpu.do_trap) qp[2]=qp[2]+1;
   qp[3+int'(dut.cpu.operands.count)]=qp[3+int'(dut.cpu.operands.count)]+1;
   if(dut.cpu.ex_valid && !dut.cpu.mem_credit) qp[6]=qp[6]+1;
   if(dut.cpu.id_valid && !dut.cpu.ex_credit) qp[7]=qp[7]+1;
   if(dut.cpu.live[dut.cpu.tail] && dut.cpu.id_valid) qp[8]=qp[8]+1;
   if(dut.cpu.ex_occupied && !dut.cpu.ex_valid) qp[9]=qp[9]+1;
  end
 end
 always @(negedge clk) if(check_stats)
  for(qi=0;qi<10;qi=qi+1) $display("QUEUE_PROFILE %0d %0d",qi,qp[qi]);
 '''
 bench.write_text(s.replace('endmodule',block+'\nendmodule'))
 files=sorted((src/'source/core').glob('*.v'))+[sim/'performance/nc_uart_sim.v',src/'source/sys_bus/nc_local_bus.v',src/'source/top/nc_soc.v',sim/'pango_ram_wide_models.v',bench]
 prefix=['wsl.exe','-d','Ubuntu','--cd',linux(OUT),'--']
 def run(args,name):
  with (OUT/name).open('wb') as log:subprocess.run([*prefix,*args],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
 run(['verilator','--binary','--timing','-j','4','-Wno-fatal','-DCOREMARK_SIM','--top-module','soc_tb','--Mdir',linux(OUT/'obj'),*[linux(f) for f in files]],'compile.log')
 image=ROOT/'sw/build/coremark_performance_10/coremark.hex'
 run([linux(OUT/'obj/Vsoc_tb'),f'+image={linux(image)}',f'+uart={linux(OUT)}/uart.txt',f'+trace={linux(OUT)}/unused.trace','+notrace=1','+limit=33000000'],'simulation.log')
 log=(OUT/'simulation.log').read_text(errors='replace');uart=(OUT/'uart.txt').read_text(errors='replace')
 assert 'COUNTER_CHECK_PASS' in log and 'CRC validation   : PASS' in uart
 metrics={s.split(':',1)[0].strip():s.split(':',1)[1].strip() for s in uart.splitlines() if ':' in s};assert int(metrics['Benchmark cycles64'])==m['benchmark_cycles']
 names='cycles id_full_pop mem_full_pop id_empty id_one id_two ex_mem_full id_queue_full id_token_busy ex_operand_wait'.split()
 counts={names[int(i)]:int(v) for i,v in re.findall(r'QUEUE_PROFILE (\d+) (\d+)',log)}
 assert len(counts)==10 and counts['id_empty']+counts['id_one']+counts['id_two']==counts['cycles']
 assert counts['cycles']==m['stats_cycles'] and counts['ex_operand_wait']==int(metrics['EX operand wait'].split()[0])
 result=dict(status='PASS',baseline=m['variant'],scope='Unchanged RTL/software observer; full-pop events are opportunities, not guaranteed cycle savings',counts=counts,input_sha256={str(f.relative_to(ROOT)):sha(f) for f in files+[image]})
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(counts,indent=2))
if __name__=='__main__':main()
