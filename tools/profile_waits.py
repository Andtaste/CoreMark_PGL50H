"""Read-only production RTL profiling; counters exist only in a copied TB."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
NAMES='cycles ex_fire ex_no_fire_recovery ex_no_fire_operand ex_no_fire_mem_full ex_no_fire_div ex_no_fire_empty operand_load_only operand_mul_only operand_load_mul operand_other id_blocked_recovery id_blocked_barrier id_blocked_irq id_blocked_ex_full id_blocked_token id_blocked_serial id_blocked_other id_full_pop_bubble mem_full_pop_bubble mem_response_wait mem_request_wait mem_head_mul_wait data_requests data_responses mem0 mem1 mem2 mem3 mem4 id0 id1 id2 other_any_alu other_any_link other_any_remaining other_alu_already_executed issue_with_completed_alu_missing_broadcast id3 memory_turnovers buffered_completion_cycles response_to_nonmemory'.split()
BLOCK=r'''
 integer pw[0:41];integer pt[0:7];integer pi;reg pl,pm,po,pa,pj,pd,pac;reg[7:0] pdone=0;
 wire late_a=dut.cpu.dep_a && pt[dut.cpu.tag_a]==0 && pdone[dut.cpu.tag_a] &&
             !(dut.cpu.f_valid && dut.cpu.f_tag==dut.cpu.tag_a) &&
             !(dut.cpu.commit && dut.cpu.w_wr && dut.cpu.w_rd!=0 && dut.cpu.w_tag==dut.cpu.tag_a);
 wire late_b=dut.cpu.dep_b && pt[dut.cpu.tag_b]==0 && pdone[dut.cpu.tag_b] &&
             !(dut.cpu.f_valid && dut.cpu.f_tag==dut.cpu.tag_b) &&
             !(dut.cpu.commit && dut.cpu.w_wr && dut.cpu.w_rd!=0 && dut.cpu.w_tag==dut.cpu.tag_b);
 task classify_dep(input integer token);
  begin
   if(pt[token]==4) pl=1;
   else if(pt[token]==6) pm=1;
   else begin po=1;if(pt[token]==0) begin pa=1;if(pdone[token]) pac=1;end
    else if(pt[token]==2 || pt[token]==3) pj=1;else pd=1;end
  end
 endtask
 initial begin for(pi=0;pi<42;pi=pi+1) pw[pi]=0;for(pi=0;pi<8;pi=pi+1) pt[pi]=0;end
 always @(posedge clk) if(rst_n) begin
  if(dut.cpu.csr.stats.control && dut.cpu.csr.stats.control_data[1]) begin
   for(pi=0;pi<42;pi=pi+1) pw[pi]=0;
  end else if(!dut.cpu.csr.stats.control && dut.cpu.csr.stats.enabled) begin
   pw[0]=pw[0]+1;
   if(dut.cpu.ex_fire) pw[1]=pw[1]+1;
   else if(dut.cpu.redirect || dut.cpu.do_trap) pw[2]=pw[2]+1;
   else if(dut.cpu.ex_occupied && !dut.cpu.ex_valid) pw[3]=pw[3]+1;
   else if(dut.cpu.ex_valid && !dut.cpu.mem_credit) pw[4]=pw[4]+1;
   else if(dut.cpu.ex_valid && !dut.cpu.execute_valid) pw[5]=pw[5]+1;
   else pw[6]=pw[6]+1;
   if(dut.cpu.ex_occupied && !dut.cpu.ex_valid) begin
    pl=0;pm=0;po=0;pa=0;pj=0;pd=0;pac=0;
    if(!dut.cpu.operands.available_a[dut.cpu.operands.rd]) classify_dep(dut.cpu.operands.dep_a[dut.cpu.operands.rd]);
    if(!dut.cpu.operands.available_b[dut.cpu.operands.rd]) classify_dep(dut.cpu.operands.dep_b[dut.cpu.operands.rd]);
    if(pl && !pm && !po) pw[7]=pw[7]+1;
    else if(pm && !pl && !po) pw[8]=pw[8]+1;
    else if(pl && pm && !po) pw[9]=pw[9]+1;
    else begin
     pw[10]=pw[10]+1;
     if(pa) pw[33]=pw[33]+1;if(pj) pw[34]=pw[34]+1;if(pd) pw[35]=pw[35]+1;
     if(pac) pw[36]=pw[36]+1;
    end
   end
   if(dut.cpu.id_valid && !dut.cpu.issue) begin
    if(dut.cpu.redirect || dut.cpu.do_trap) pw[11]=pw[11]+1;
    else if(dut.cpu.barrier) pw[12]=pw[12]+1;
    else if(dut.cpu.irq_pending) pw[13]=pw[13]+1;
    else if(!dut.cpu.ex_credit) pw[14]=pw[14]+1;
    else if(dut.cpu.live[dut.cpu.tail]) pw[15]=pw[15]+1;
    else if((dut.cpu.id_serial || dut.cpu.id_fault) && dut.cpu.live!=0) pw[16]=pw[16]+1;
    else pw[17]=pw[17]+1;
   end
   if(dut.cpu.id_valid && !dut.cpu.ex_credit && dut.cpu.ex_valid && dut.cpu.ex_pop &&
      !dut.cpu.redirect && !dut.cpu.do_trap) pw[18]=pw[18]+1;
   if(dut.cpu.execute_valid && !dut.cpu.mem_credit && dut.cpu.mem_valid && dut.cpu.memory_ready &&
      !dut.cpu.redirect && !dut.cpu.do_trap) pw[19]=pw[19]+1;
   if(dut.cpu.memory.memory_pending) pw[20]=pw[20]+1;
   if(dut.cpu.d_req_valid && !dut.cpu.d_req_ready) pw[21]=pw[21]+1;
   if(dut.cpu.mem_valid && dut.cpu.memory.input_multiply && !dut.cpu.memory.state && !dut.cpu.mul_query_ready) pw[22]=pw[22]+1;
   if(dut.cpu.d_req_valid && dut.cpu.d_req_ready) pw[23]=pw[23]+1;
   if(dut.cpu.d_rsp_valid && dut.cpu.d_rsp_ready) pw[24]=pw[24]+1;
   pw[25+int'(dut.cpu.memory_queue.count)]=pw[25+int'(dut.cpu.memory_queue.count)]+1;
   if(dut.cpu.operands.count==3) pw[38]=pw[38]+1;
   else pw[30+int'(dut.cpu.operands.count)]=pw[30+int'(dut.cpu.operands.count)]+1;
   if(dut.cpu.issue && (late_a || late_b)) pw[37]=pw[37]+1;
   if(dut.cpu.d_req_valid && dut.cpu.d_req_ready && dut.cpu.memory.memory_pending) pw[39]=pw[39]+1;
   if(dut.cpu.memory.buffered) pw[40]=pw[40]+1;
   if(dut.cpu.memory.turnover && dut.cpu.mem_valid && dut.cpu.memory_ready && !dut.cpu.memory.input_memory) pw[41]=pw[41]+1;
  end
  if(dut.cpu.ex_fire && !dut.cpu.execute_packet[2] && dut.cpu.execute_packet[7:4]==0) pdone[dut.cpu.ex_tag]=1;
  if(dut.cpu.issue) begin
   pt[dut.cpu.tail]=(dut.cpu.id_kind==6 && dut.cpu.id_insn[14]) ? 7 : int'(dut.cpu.id_kind);
   pdone[dut.cpu.tail]=0;
  end
 end
 always @(negedge clk) if(check_stats) begin
  for(pi=0;pi<42;pi=pi+1) $display("WAIT_PROFILE %0d %0d",pi,pw[pi]);
 end
'''

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--baseline',default='docs/stage_opt/validation/baseline.json')
    parser.add_argument('--reference',default='simulation/results/coremark_performance_10_verilator_stage_final/result.json')
    parser.add_argument('--result-tag',default='stage_final')
    args=parser.parse_args();assert re.fullmatch(r'[A-Za-z0-9_-]+',args.result_tag)
    out=ROOT/('simulation/results/wait_profile_'+args.result_tag);out.mkdir(parents=True,exist_ok=True)
    final=json.loads((ROOT/args.reference).read_text())
    sta=json.loads((ROOT/args.baseline).read_text())
    source=ROOT/'simulation/tb/soc_tb.v';tb=out/'soc_tb_profile.v'
    tb.write_text(source.read_text().replace(' defparam dut.bus.uart.BAUD=9375000;','').replace('endmodule',BLOCK+'\nendmodule'))
    us=ROOT/'hardware/pds/source/perips/nc_uart.v';uart=out/'nc_uart_sim.v'
    uart.write_text(us.read_text().replace('BAUD=115200','BAUD=9375000'))
    rtl=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[])
    model=ROOT/'simulation/models/pango_ram_models.v';image=ROOT/'sw/build/coremark_performance_10/coremark.hex'
    inputs=rtl+[source,model,image,Path(__file__).resolve()]
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    def linux(p):
        p=Path(p).resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
    prefix=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--']
    sources=[p for p in rtl if p!=us]+[uart,model,tb]
    with (out/'compile.log').open('w') as f:
        subprocess.run([*prefix,'verilator','--binary','--timing','-j','4','-Wno-fatal','-DCOREMARK_SIM','--top-module','soc_tb','--Mdir',linux(out/'obj'),*[linux(p) for p in sources]],stdout=f,stderr=subprocess.STDOUT,check=True)
    with (out/'simulation.log').open('w') as f:
        subprocess.run([*prefix,linux(out/'obj/Vsoc_tb'),f'+image={linux(image)}',f'+trace={linux(out)}/retire.trace',f'+uart={linux(out)}/uart.txt','+notrace=1','+limit=33000000'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
    log=(out/'simulation.log').read_text(encoding='utf-8',errors='replace');text=(out/'uart.txt').read_text(encoding='utf-8')
    counts={NAMES[int(i)]:int(v) for i,v in re.findall(r'WAIT_PROFILE (\d+) (\d+)',log)}
    assert len(counts)==len(NAMES)==42
    assert sum(counts[k] for k in NAMES[1:7])==counts['cycles']
    assert sum(counts[k] for k in NAMES[7:11])==int(final['metrics']['EX operand wait'].split()[0])
    assert sum(counts[k] for k in NAMES[11:18])==int(final['metrics']['ID blocked cycles'].split()[0])
    assert sum(counts[k] for k in NAMES[25:30])==counts['cycles']
    assert sum(counts[k] for k in ('id0','id1','id2','id3'))==counts['cycles']
    expected=f"COUNTER_CHECK_PASS cycles={final['metrics']['Stats window cycles']} retired={final['metrics']['Retired instructions']}"
    assert expected in log and 'CRC validation   : PASS' in text
    for key,value in final['metrics'].items():
        if key=='Software build':continue
        assert any(line.split(':',1)[0].strip()==key and line.split(':',1)[1].strip()==value for line in text.splitlines() if ':' in line),key
    for name,sha in hashes.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    for name,sha in sta['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    result=dict(status='PASS',scope='simulation-only observer; production RTL and software unchanged',counts=counts,input_sha256=hashes,
        tb_sha256=hashlib.sha256(tb.read_bytes()).hexdigest(),uart_sim_sha256=hashlib.sha256(uart.read_bytes()).hexdigest(),
        notes=['Wait classes overlap across stages.','Full-pop bubbles are opportunities observed under existing credit protocol, not guaranteed total-cycle savings.',
               'Other ALU waits were checked against an observer tracking EX completion, not inferred from producer opcode alone.'])
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['counts'],indent=2))

if __name__=='__main__':main()
