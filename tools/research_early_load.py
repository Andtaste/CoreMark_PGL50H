"""Integrate RF-only prepared loads in isolated copies, never production RTL."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def linux(p):
    p=Path(p).resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def replace(text,old,new):
    assert text.count(old)==1,(old,text.count(old));return text.replace(old,new)
def transform(core,operands,memory):
    operands=replace(operands,'input wire wait_a,wait_b,input wire[2:0] tag_a,tag_b,',
        '''input wire wait_a,wait_b,input wire[2:0] tag_a,tag_b,
 input wire in_early_load,input wire[31:0] in_early_address,
 output wire early_load,output wire[31:0] early_address,''')
    operands=replace(operands,'reg[203:0] payload[0:1];', '''// Load does not use csr_old. Reuse that registered payload word for
 // its ID-prepared address; architectural base operands are unchanged.
 reg[1:0] prepared_load;
 assign early_load=count!=0 && prepared_load[rd];
 assign early_address=payload[rd][39:8];
 reg[203:0] payload[0:1];''')
    operands=replace(operands,'payload[wr]<=in_packet;', '''payload[wr]<={in_packet[203:40],
    (in_packet[203:200]==4 ? in_early_address : in_packet[39:8]),in_packet[7:0]};
   prepared_load[wr]<=in_early_load;''')
    memory=replace(memory,'input wire rsp_valid,output wire rsp_ready,',
        'output wire early_window,\n input wire rsp_valid,output wire rsp_ready,')
    memory=replace(memory,'assign ready=can_accept', '''// Registered state/held flags and registered bus error/valid only.
 // Independent of incoming packet/data and returned RAM data: no loop
 // through early selection, no dependency on operand forwarding.
 assign early_window=can_accept && !(buffered && serial);
 assign ready=can_accept''')
    core=replace(core,'wire ex_credit,ex_valid,ex_pop,ex_occupied;',
        'wire prepared_load;wire[31:0] prepared_address;wire early_offer,ex_flow_credit;\n wire ex_credit,ex_valid,ex_pop,ex_occupied;')
    core=replace(core,'.wait_a(dep_a),.wait_b(dep_b),.tag_a(tag_a),.tag_b(tag_b),',
        '''.wait_a(dep_a),.wait_b(dep_b),.tag_a(tag_a),.tag_b(tag_b),
  .in_early_load(id_kind==4 && !dep_a && !id_illegal && !id_fault),
  .in_early_address(a+id_imm),.early_load(prepared_load),.early_address(prepared_address),''')
    core=replace(core,'.out_valid(execute_valid),.out_ready(mem_credit)',
        '.out_valid(execute_valid),.out_ready(ex_flow_credit)')
    core=replace(core,'wire ex_fire=execute_valid && mem_credit;',
        'wire ex_fire=execute_valid && ex_flow_credit;')
    core=replace(core,'.in_valid(execute_valid),.in_ready(mem_credit)',
        '.in_valid(execute_valid && !early_offer),.in_ready(mem_credit)')
    block='''
 // Research-only early RAM read. Its address is already in ID/EX payload
 // registers. No selected/freshly forwarded operand or EX adder participates
 // in request address or authorization. Older queue entries always win.
 wire memory_early_window,selected_memory_ready;
 wire prepared_ram=prepared_address<32'h00010000 ||
  (prepared_address>=32'h10000000 && prepared_address<32'h10008000);
 wire[2:0] prepared_f3=ex_packet[150:148];
 wire prepared_aligned=prepared_f3[1:0]==2 ? ~|prepared_address[1:0] :
                       prepared_f3[1:0]==1 ? !prepared_address[0] : 1'b1;
 assign early_offer=prepared_load && prepared_ram && prepared_aligned &&
  !mem_valid && memory_early_window && ex_enable && (!wb_valid || !w_serial);
 assign ex_flow_credit=early_offer ? selected_memory_ready : mem_credit;
 // A bus stall holds the ID/EX head. No bypassed instruction is also
 // enqueued. Input credits of both FIFOs still use registered occupancy.
 // early_offer implies an EMPTY queue, whose out_valid is zero. Its pop
 // cannot fire regardless of ready. Keep MEM-ready / CSR busy semantics.
 assign memory_ready=selected_memory_ready;
 wire[31:0] prepared_next=ex_packet[199:168]+32'd4;
 wire[279:0] early_packet={ex_tag,ex_packet[199:168],ex_packet[167:136],prepared_next,
  32'b0,prepared_address,96'b0,5'b0,ex_packet[7:3],prepared_f3,4'd4,4'b1000};
 wire[279:0] selected_memory_packet=early_offer ? early_packet : mem_packet;
'''
    core=replace(core,' nc_memory memory(',block+' nc_memory memory(')
    core=replace(core,'.valid(mem_valid),.ready(memory_ready),.packet(mem_packet)',
        '.valid(mem_valid || early_offer),.ready(selected_memory_ready),.packet(selected_memory_packet)')
    core=replace(core,'.req_valid(d_req_valid),.req_ready(d_req_ready)',
        '.early_window(memory_early_window),\n  .req_valid(d_req_valid),.req_ready(d_req_ready)')
    return core,operands,memory

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--validation',action='store_true');ap.add_argument('--generate-only',action='store_true');ap.add_argument('--predecode',action='store_true');a=ap.parse_args()
    variant='early_load_predecode' if a.predecode else 'early_load'
    base=ROOT/'hardware/pds/source/core';out=ROOT/('simulation/results/load_bp_'+variant);out.mkdir(parents=True,exist_ok=True)
    accepted=ROOT/'docs/accepted_baseline.json';sta=ROOT/'hardware/pds/report_timing/top.rtr'
    b=json.loads(accepted.read_text());preserve={p:sha(p) for p in (accepted,sta)}
    for n,h in b['source_sha256'].items():assert sha(ROOT/n)==h,n
    overrides={}
    c,o,m=transform(*[(base/n).read_text() for n in ('nc_core.v','nc_operands.v','nc_memory.v')])
    if a.predecode:
        # Terminate address range/alignment qualification at ID/EX. This
        # removes prepared-address -> early select -> bus address/CE control.
        o=replace(o,'prepared_load[wr]<=in_early_load;', '''prepared_load[wr]<=in_early_load &&
    (in_early_address<32'h00010000 ||
     (in_early_address>=32'h10000000 && in_early_address<32'h10008000)) &&
    (in_packet[149:148]==2 ? ~|in_early_address[1:0] :
     in_packet[149:148]==1 ? !in_early_address[0] : 1'b1);''')
        c=replace(c,'assign early_offer=prepared_load && prepared_ram && prepared_aligned &&',
            'assign early_offer=prepared_load &&')
    for name,src in zip(('nc_core.v','nc_operands.v','nc_memory.v'),(c,o,m)):
        q=out/name
        if not q.exists() or q.read_text()!=src:q.write_text(src)
        overrides[base/name]=q
    if a.generate_only:print('Generated isolated early_load candidate');return
    result_dir=out/('validation' if a.validation else 'performance');result_dir.mkdir(exist_ok=True)
    rtl=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[])
    obs=ROOT/'simulation/research/early_load_observer.vh';source_tb=ROOT/'simulation/tb/soc_tb.v';model=ROOT/'simulation/models/pango_ram_models.v'
    image=ROOT/('sw/build/coremark_validation_1/coremark.hex' if a.validation else 'sw/build/coremark_performance_10/coremark.hex')
    inputs=rtl+[obs,source_tb,model,image,Path(__file__).resolve()];hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    (result_dir/'tool_snapshot.py').write_bytes(Path(__file__).read_bytes())
    uart_src=ROOT/'hardware/pds/source/perips/nc_uart.v';uart=out/'nc_uart_sim.v'
    uart.write_text(uart_src.read_text().replace('BAUD=115200','BAUD=9375000'))
    tb=out/'soc_tb_sim.v';tb.write_text(source_tb.read_text().replace(' defparam dut.bus.uart.BAUD=9375000;','').replace('endmodule',obs.read_text()+'\nendmodule'))
    actual=[overrides.get(p,p) for p in rtl if p!=uart_src]+[uart,model,tb]
    prefix=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--']
    def run(cmd,log,timeout=600):
        with log.open('w') as f:r=subprocess.run(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
        assert r.returncode==0,(log,log.read_text(errors='replace')[-4000:])
    run([*prefix,'verilator','--binary','--timing','-j','4','-Wno-fatal','-DCOREMARK_SIM','--top-module','soc_tb','--Mdir',linux(out/'obj'),*[linux(p) for p in actual]],result_dir/'compile.log')
    run([*prefix,linux(out/'obj/Vsoc_tb'),f'+image={linux(image)}',f'+trace={linux(result_dir)}/unused.trace',f'+uart={linux(result_dir)}/uart.txt','+notrace=1','+limit=33000000'],result_dir/'simulation.log')
    log=(result_dir/'simulation.log').read_text(errors='replace');u=(result_dir/'uart.txt').read_text()
    assert 'COUNTER_CHECK_PASS' in log and 'CRC validation   : PASS' in u and 'PASS cycles=' in log
    metrics={s.split(':',1)[0].strip():s.split(':',1)[1].strip() for s in u.splitlines() if ':' in s}
    ref=json.loads((ROOT/('simulation/results/coremark_validation_1_verilator_exid_final/result.json' if a.validation else 'simulation/results/coremark_performance_10_verilator_exid_aux/result.json')).read_text())
    for k in ('Retired instructions','Retired loads','Retired stores','BJP instructions','seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal'):assert metrics[k]==ref['metrics'][k],k
    for n,h in hashes.items():assert sha(ROOT/n)==h,n
    for p,h in preserve.items():assert sha(p)==h,p
    result=dict(status='PASS',variant=variant,scope='Isolated full CPU candidate, not adopted',metrics=metrics,
        input_sha256=hashes,override_sha256={str(p.relative_to(ROOT)):sha(q) for p,q in overrides.items()},actual_compile_sha256={str(p.relative_to(ROOT)):sha(p) for p in actual},image_sha256=sha(image))
    for key,marker in (('predictor','PREDICTOR_STATS'),('multiply','MULTIPLY_STATS'),('early_load','EARLY_LOAD_STATS')):
        m=re.search(marker+r' ([^\r\n]+)',log);assert m;result[key]={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])}
    save(result_dir/'result.json',result)
    if not a.validation:save(out/'result.json',result)
    print(json.dumps(dict(cycles=int(metrics['Stats window cycles']),ipc=int(metrics['Retired instructions'])/int(metrics['Stats window cycles']),early_load=result['early_load']),indent=2))
if __name__=='__main__':main()
