"""Rank equal-size BTB hashes from a diagnostic resolved-branch trace.

This idealized sequential predictor model ignores fetch/training latency and
speculative execution. Ranking is advisory; only full RTL runs establish gains.
"""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'simulation/results/autonomous_20261022/btb_hash_profile'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def linux(p):return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def main():
 m=json.loads((ROOT/'docs/active_optimization_baseline.json').read_text());src=ROOT/m['project_directory']
 for n,h in m['input_sha256'].items():assert sha(src/n)==h,n
 OUT.mkdir(exist_ok=True)
 sim=ROOT/f"simulation/results/load_bp_dual_boundary_auto_{m['source_trial']}"
 bench=OUT/'soc_tb.v';s=(sim/'performance/soc_tb.v').read_text()
 s=s.replace('endmodule','''
 integer hash_fd;
 initial hash_fd=$fopen("btb_events.trace","w");
 always @(posedge clk) if(rst_n) begin
  if(dut.cpu.bp_flush) $fdisplay(hash_fd,"F");
  else if(dut.cpu.bp_update_valid)
   $fdisplay(hash_fd,"%08x %08x %0d %0d %0d %0d",dut.cpu.bp_update_pc,dut.cpu.bp_update_target,
     dut.cpu.bp_update_branch,dut.cpu.bp_update_conditional,dut.cpu.bp_update_taken,dut.cpu.csr.stats.enabled);
 end
 endmodule''');bench.write_text(s)
 files=sorted((src/'source/core').glob('*.v'))+[sim/'performance/nc_uart_sim.v',src/'source/sys_bus/nc_local_bus.v',src/'source/top/nc_soc.v',sim/'pango_ram_wide_models.v',bench]
 prefix=['wsl.exe','-d','Ubuntu','--cd',linux(OUT),'--']
 def run(args,name,timeout=600):
  with (OUT/name).open('wb') as log:subprocess.run([*prefix,*args],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=timeout)
 if '--analyze-only' not in sys.argv:run(['verilator','--binary','--timing','-j','4','-Wno-fatal','-DCOREMARK_SIM','--top-module','soc_tb','--Mdir',linux(OUT/'obj'),*[linux(f) for f in files]],'compile.log')
 image=ROOT/'sw/build/coremark_performance_10/coremark.hex'
 if '--analyze-only' not in sys.argv:run([linux(OUT/'obj/Vsoc_tb'),f'+image={linux(image)}',f'+uart={linux(OUT)}/uart.txt',f'+trace={linux(OUT)}/unused.trace','+notrace=1','+limit=33000000'],'simulation.log')
 log=(OUT/'simulation.log').read_text(errors='replace');uart=(OUT/'uart.txt').read_text(errors='replace')
 assert 'COUNTER_CHECK_PASS' in log and 'CRC validation   : PASS' in uart
 metrics={s.split(':',1)[0].strip():s.split(':',1)[1].strip() for s in uart.splitlines() if ':' in s}
 assert int(metrics['Benchmark cycles64'])==m['benchmark_cycles']
 raw=OUT/'btb_events.trace';events=[]
 for line in raw.read_text().splitlines():
  if line=='F':events.append(None);continue
  v=line.split();events.append((int(v[0],16),int(v[1],16),*[int(x) for x in v[2:]]))
 results=[]
 for shift in range(8,15):
  for rotate in range(5):
   table=[None]*64;miss=direction=targetwrong=count=0
   for event in events:
    if event is None:table=[None]*64;continue
    pc,target,branch,conditional,taken,measured=event
    upper=(pc>>shift)&31;fold=((upper<<rotate)|(upper>>(5-rotate)))&31
    index=(((pc>>3)^fold)&31)*2+((pc>>2)&1)
    entry=table[index];hit=entry is not None and entry[0]==pc
    if branch:
     predicted=hit and (not entry[2] or entry[4+entry[3]]>=2)
     predicted_next=entry[1] if predicted else (pc+4)&0xffffffff
     actual_next=target if taken else (pc+4)&0xffffffff
     if measured:
      count+=1;miss+=predicted_next!=actual_next;direction+=predicted!=bool(taken)
      targetwrong+=bool(predicted and taken and entry[1]!=target)
     if not conditional:table[index]=[pc,target,0,0,3,3]
     elif not hit:table[index]=[pc,target,1,taken,2 if taken else 1,2 if taken else 1]
     else:
      pos=4+entry[3];entry[pos]=min(3,entry[pos]+1) if taken else max(0,entry[pos]-1)
      entry[1]=target;entry[2]=1;entry[3]=taken
    elif hit:table[index]=None
   results.append(dict(shift=shift,rotate=rotate,branches=count,next_pc_wrong=miss,direction_wrong=direction,target_wrong=targetwrong))
 results.sort(key=lambda x:x['next_pc_wrong'])
 result=dict(status='PASS',scope='Advisory sequential resolved-trace model, not a cycle or throughput result; unchanged capacity and full PC tags',baseline=m['variant'],benchmark_cycles=m['benchmark_cycles'],trace_sha256=sha(raw),event_count=len(events),input_sha256={str(f.relative_to(ROOT)):sha(f) for f in files+[image]},ranking=results)
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 for row in results[:10]:print(row)
 print('CURRENT',next(x for x in results if x['shift']==10 and x['rotate']==0))
if __name__=='__main__':main()
