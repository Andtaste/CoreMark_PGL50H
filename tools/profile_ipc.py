"""Observe branch causes and load dependency age without changing production RTL."""
from pathlib import Path
from collections import Counter, defaultdict
import argparse, gzip, hashlib, json, re, subprocess
ROOT=Path(__file__).resolve().parents[1]
BLOCK=r'''
 integer ipc_fd,ipc_i,ipc_cycle=0;
 integer load_phase[0:7];integer load_wait_phase[0:4];integer load_req_age[0:31];
 integer load_ex_cycle[0:7];integer load_req_cycle[0:7];integer load_rsp_age[0:31];
 reg[1023:0] ipc_file;reg ipc_wait_load;integer ipc_phase,ipc_age;
 initial begin
  if(!$value$plusargs("ipctrace=%s",ipc_file)) $fatal(1,"missing IPC trace");
  ipc_fd=$fopen(ipc_file,"w");
  for(ipc_i=0;ipc_i<8;ipc_i=ipc_i+1) begin load_phase[ipc_i]=0;load_ex_cycle[ipc_i]=0;load_req_cycle[ipc_i]=0;end
  for(ipc_i=0;ipc_i<5;ipc_i=ipc_i+1) load_wait_phase[ipc_i]=0;
  for(ipc_i=0;ipc_i<32;ipc_i=ipc_i+1) begin load_req_age[ipc_i]=0;load_rsp_age[ipc_i]=0;end
 end
 always @(posedge clk) if(rst_n) begin
  ipc_cycle=ipc_cycle+1;
  if(!dut.cpu.csr.stats.control && dut.cpu.csr.stats.enabled) begin
   if(dut.cpu.ex_fire && dut.cpu.ex_branch && !dut.cpu.execute_packet[2])
    $fdisplay(ipc_fd,"B %08x %08x %08x %08x %01x",dut.cpu.execute_packet[276:245],dut.cpu.ex_packet[167:136],dut.cpu.ex_prediction,dut.cpu.execute_target,dut.cpu.execute_taken);
   if(dut.cpu.ex_occupied && !dut.cpu.ex_valid) begin
    ipc_wait_load=0;ipc_phase=0;
    if(!dut.cpu.operands.available_a[dut.cpu.operands.rd] && load_phase[dut.cpu.operands.dep_a[dut.cpu.operands.rd]]!=0) begin
     ipc_wait_load=1;ipc_phase=load_phase[dut.cpu.operands.dep_a[dut.cpu.operands.rd]];
    end
    if(!dut.cpu.operands.available_b[dut.cpu.operands.rd] && load_phase[dut.cpu.operands.dep_b[dut.cpu.operands.rd]]!=0) begin
     ipc_wait_load=1;
     if(ipc_phase==0 || load_phase[dut.cpu.operands.dep_b[dut.cpu.operands.rd]]<ipc_phase) ipc_phase=load_phase[dut.cpu.operands.dep_b[dut.cpu.operands.rd]];
    end
    if(ipc_wait_load) load_wait_phase[ipc_phase]=load_wait_phase[ipc_phase]+1;
   end
   if(dut.cpu.d_req_valid && dut.cpu.d_req_ready && !dut.cpu.d_write) begin
    ipc_age=ipc_cycle-load_ex_cycle[dut.cpu.mem_packet[279:277]];
    if(ipc_age>31) ipc_age=31;load_req_age[ipc_age]=load_req_age[ipc_age]+1;
   end
   if(dut.cpu.memory_done && dut.cpu.memory_packet[7:4]==4) begin
    ipc_age=ipc_cycle-load_req_cycle[dut.cpu.memory_packet[279:277]];
    if(ipc_age>31) ipc_age=31;load_rsp_age[ipc_age]=load_rsp_age[ipc_age]+1;
   end
  end
  // Classify before the edge, then record transitions at the edge.
  if(dut.cpu.commit) load_phase[dut.cpu.w_tag]=0;
  if(dut.cpu.memory_done && dut.cpu.memory_packet[7:4]==4) load_phase[dut.cpu.memory_packet[279:277]]=4;
  if(dut.cpu.d_req_valid && dut.cpu.d_req_ready && !dut.cpu.d_write) begin
   load_phase[dut.cpu.mem_packet[279:277]]=3;load_req_cycle[dut.cpu.mem_packet[279:277]]=ipc_cycle;
  end
  if(dut.cpu.ex_fire && dut.cpu.execute_packet[7:4]==4) begin
   load_phase[dut.cpu.ex_tag]=2;load_ex_cycle[dut.cpu.ex_tag]=ipc_cycle;
  end
  if(dut.cpu.issue) load_phase[dut.cpu.tail]=dut.cpu.id_kind==4 ? 1 : 0;
 end
 always @(negedge clk) if(check_stats) begin
  for(ipc_i=0;ipc_i<5;ipc_i=ipc_i+1) $display("LOAD_PHASE %0d %0d",ipc_i,load_wait_phase[ipc_i]);
  for(ipc_i=0;ipc_i<32;ipc_i=ipc_i+1) begin
   $display("LOAD_REQ_AGE %0d %0d",ipc_i,load_req_age[ipc_i]);$display("LOAD_RSP_AGE %0d %0d",ipc_i,load_rsp_age[ipc_i]);
  end
  $fclose(ipc_fd);ipc_fd=0;
 end
'''

def analyze(trace):
    pcs=defaultdict(Counter);rows=[]
    with gzip.open(trace,'rt') as f:
        for line in f:
            _,p,i,pr,t,a=line.split();pc,insn,pred,target,taken=[int(x,16) for x in (p,i,pr,t,a)]
            hit=pred>>31;pt=(pred>>30)&1;cond=insn&127==0x63
            c=pcs[f'{pc:08x}'];c['count']+=1;c['conditional']+=cond;c['taken']+=taken;c['miss']+=not hit
            c['direction_wrong']+=pt!=taken;c['miss_direction_wrong']+=(not hit and pt!=taken)
            c['hit_direction_wrong']+=(hit and pt!=taken)
            c['target_wrong']+=pt and taken and (pred&0x3fffffff)<<2!=target
            rows.append((pc,cond,taken,target))
    # Direction/BTB models use resolved architectural outcomes, immediate
    # training, no speculative lookup latency. Screening only, not an RTL score.
    models={}
    for bits,hashed in ((6,False),(6,True),(7,False),(7,True),(8,True)):
        table={};wrong=misses=0
        for pc,cond,taken,target in rows:
            mask=(1<<bits)-1;idx=((pc>>2)^((pc>>(bits+2)) if hashed else 0))&mask
            old=table.get(idx);hit=old is not None and old[0]==pc
            prediction=hit and (not old[1] or old[2]>=2)
            wrong+=prediction!=taken;misses+=not hit
            state=(min(3,old[2]+1) if taken else max(0,old[2]-1)) if hit else (2 if taken else 1)
            table[idx]=(pc,cond,state if cond else 3,target)
        models[f'btb{1<<bits}_'+('xor' if hashed else 'direct')]=dict(direction_wrong=wrong,misses=misses)
    return dict(branches=len(rows),totals=dict(sum(pcs.values(),Counter())),by_pc=dict(sorted(pcs.items(),key=lambda x:-x[1]['direction_wrong'])),screening=models)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);ap.add_argument('--reference',required=True);ap.add_argument('--analyze-only',action='store_true');a=ap.parse_args()
    assert re.fullmatch(r'[A-Za-z0-9_-]+',a.tag)
    out=ROOT/('simulation/results/ipc_profile_'+a.tag);out.mkdir(parents=True,exist_ok=True)
    ref=json.loads((ROOT/a.reference).read_text());trace=out/'branches.txt';gz=out/'branches.txt.gz'
    if not a.analyze_only:
        src=ROOT/'simulation/tb/soc_tb.v';uart_src=ROOT/'hardware/pds/source/perips/nc_uart.v'
        rtl=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[])
        model=ROOT/'simulation/models/pango_ram_models.v';image=ROOT/'sw/build/coremark_performance_10/coremark.hex'
        inputs=rtl+[src,model,image,Path(__file__).resolve()];hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
        tb=out/'soc_tb_ipc.v';tb.write_text(src.read_text().replace(' defparam dut.bus.uart.BAUD=9375000;','').replace('endmodule',BLOCK+'\nendmodule'))
        uart=out/'nc_uart_sim.v';uart.write_text(uart_src.read_text().replace('BAUD=115200','BAUD=9375000'))
        def linux(p):
            p=Path(p).resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
        prefix=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--']
        with (out/'compile.log').open('w') as f:
            subprocess.run([*prefix,'verilator','--binary','--timing','-j','4','-Wno-fatal','-DCOREMARK_SIM','--top-module','soc_tb','--Mdir',linux(out/'obj'),*[linux(p) for p in rtl if p!=uart_src],linux(uart),linux(model),linux(tb)],stdout=f,stderr=subprocess.STDOUT,check=True)
        with (out/'simulation.log').open('w') as f:
            subprocess.run([*prefix,linux(out/'obj/Vsoc_tb'),f'+image={linux(image)}',f'+trace={linux(out)}/unused.trace',f'+ipctrace={linux(trace)}',f'+uart={linux(out)}/uart.txt','+notrace=1','+limit=33000000'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
        log=(out/'simulation.log').read_text(errors='replace');uart_text=(out/'uart.txt').read_text()
        for k,v in ref['metrics'].items():
            assert any(s.split(':',1)[0].strip()==k and s.split(':',1)[1].strip()==v for s in uart_text.splitlines() if ':' in s),k
        assert 'COUNTER_CHECK_PASS' in log and 'CRC validation   : PASS' in uart_text
        for n,h in hashes.items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,n
        with trace.open('rb') as f,gzip.open(gz,'wb') as g:
            for b in iter(lambda:f.read(1<<20),b''):g.write(b)
        collection=dict(status='PASS',input_sha256=hashes,reference=a.reference,
            load_wait_phase={int(i):int(v) for i,v in re.findall(r'LOAD_PHASE (\d+) (\d+)',log)},
            load_ex_to_request={int(i):int(v) for i,v in re.findall(r'LOAD_REQ_AGE (\d+) (\d+)',log) if int(v)},
            load_request_to_wb_capture={int(i):int(v) for i,v in re.findall(r'LOAD_RSP_AGE (\d+) (\d+)',log) if int(v)})
        (out/'collection.json').write_text(json.dumps(collection,indent=2)+'\n');trace.unlink()
    result=analyze(gz);result['scope']='Same-window RTL observation; screening models omit speculative timing.'
    assert result['branches']==ref['predictor']['resolved']
    for k in ('direction_wrong','target_wrong'):assert result['totals'][k]==ref['predictor'][k],k
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='by_pc'},indent=2))
    print((out/'collection.json').read_text());print('Top branch PCs:',list(result['by_pc'].items())[:12])
if __name__=='__main__':main()
