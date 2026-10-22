"""Isolated folded-BTB / resolved-only RAS experiments. Production is read-only."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def linux(p):
    p=Path(p).resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def replace(s,old,new):assert s.count(old)==1,(old,s.count(old));return s.replace(old,new)
def generate(variant):
    btb=(ROOT/'hardware/pds/source/core/nc_btb.v').read_text();overrides={}
    folded=variant in ('bp_fold','bp_combo');ras=variant in ('bp_ras','bp_combo')
    if folded:
        btb=btb.replace('reg[63:0] valid;','reg[127:0] valid;').replace('reg[23:0] tags[0:63]','reg[22:0] tags[0:127]').replace('[0:63]','[0:127]')
        btb=replace(btb,'wire[5:0] r=lookup_pc[7:2],w=update_pc[7:2];',
            'wire[6:0] r=lookup_pc[8:2] ^ lookup_pc[15:9],w=update_pc[8:2] ^ update_pc[15:9];')
        btb=btb.replace('lookup_pc[31:8]','lookup_pc[31:9]').replace('update_pc[31:8]','update_pc[31:9]')
        btb=btb.replace('// 64 direct-mapped entries. Full PC tag [31:8], word target.',
            '// 128 direct-mapped entries; index PC[8:2] XOR PC[15:9], full tag PC[31:9].')
    if ras:
        btb=replace(btb,'input wire update_valid,update_branch,update_conditional,update_taken,',
            'input wire update_valid,update_branch,update_conditional,update_taken,update_call,update_pop,')
        btb=replace(btb,'assign prediction={hit,predict_taken,targets[r]};', '''// Return type and cached top select in parallel with tag comparison.
 // No hit -> 30-bit target mux cascade, no live stack-array read on IF.
 wire use_ras=return_entry[r] && ras_count!=0;
 assign prediction={hit,predict_taken,(use_ras ? ras_top : targets[r])};''')
        block='''
 // Resolved-only stack, driven exclusively by registered training hints.
 // No speculative push/pop, fetch-to-training bypass or history rollback.
 reg return_entry[0:ENTRIES_MINUS_ONE] /* synthesis syn_ramstyle="lut_ram" */;
 reg[29:0] ras_mem[0:3] /* synthesis syn_ramstyle="lut_ram" */;
 reg[29:0] ras_top;
 reg[1:0] ras_sp;reg[2:0] ras_count;
 wire[1:0] ras_previous=ras_sp-2'd1;
 wire[1:0] ras_push_index=ras_count==0 ? 2'd0 : update_pop ? ras_sp : ras_sp+2'd1;
 wire[29:0] ras_link=update_pc[31:2]+30'd1;
 always @(posedge clk) if(update_valid && update_branch && !flush) begin
  return_entry[w]<=update_pop;
  if(update_call) begin ras_mem[ras_push_index]<=ras_link;ras_top<=ras_link;end
  else if(update_pop && ras_count>1) ras_top<=ras_mem[ras_previous];
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin ras_sp<=0;ras_count<=0;end
  else if(flush) begin ras_sp<=0;ras_count<=0;end
  else if(update_valid && update_branch) begin
   if(update_call) begin
    ras_sp<=ras_push_index;
    if(ras_count==0) ras_count<=1;
    else if(!update_pop && ras_count<4) ras_count<=ras_count+3'd1;
   end else if(update_pop && ras_count!=0) begin
    ras_count<=ras_count-3'd1;
    if(ras_count>1) ras_sp<=ras_previous;
   end
  end
 end
'''.replace('ENTRIES_MINUS_ONE','127' if folded else '63')
        btb=replace(btb,'endmodule',block+'endmodule')
        core=(ROOT/'hardware/pds/source/core/nc_core.v').read_text();fetch=(ROOT/'hardware/pds/source/core/nc_fetch.v').read_text()
        core=replace(core,'reg bp_update_valid,','reg bp_update_call,bp_update_pop;\n reg bp_update_valid,')
        core=replace(core,'.bp_flush(bp_flush),.bp_update_valid(bp_update_valid),',
            '.bp_update_call(bp_update_call),.bp_update_pop(bp_update_pop),\n  .bp_flush(bp_flush),.bp_update_valid(bp_update_valid),')
        core=replace(core,'always @(posedge clk) begin\n  bp_update_pc<=', '''// Decode call/return hints only from registered EX instruction bits.
 // The two hints cross FFs beside existing training, never raw EX -> IF.
 wire[31:0] ras_insn=ex_packet[167:136];
 wire ras_rd_link=ras_insn[11:7]==1 || ras_insn[11:7]==5;
 wire ras_rs_link=ras_insn[19:15]==1 || ras_insn[19:15]==5;
 always @(posedge clk) begin
  bp_update_call<=(ras_insn[6:0]==7'h6f || ras_insn[6:0]==7'h67) && ras_rd_link;
  bp_update_pop<=ras_insn[6:0]==7'h67 && ras_rs_link && (!ras_rd_link || ras_insn[11:7]!=ras_insn[19:15]);
  bp_update_pc<=''')
        fetch=replace(fetch,'input wire bp_flush,bp_update_valid,',
            'input wire bp_update_call,bp_update_pop,\n input wire bp_flush,bp_update_valid,')
        fetch=replace(fetch,'.update_valid(bp_update_valid),.update_branch(bp_update_branch)',
            '.update_call(bp_update_call),.update_pop(bp_update_pop),\n   .update_valid(bp_update_valid),.update_branch(bp_update_branch)')
        overrides.update({'nc_core.v':core,'nc_fetch.v':fetch})
    overrides['nc_btb.v']=btb
    return overrides
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True,choices=('bp_fold','bp_ras','bp_combo'));ap.add_argument('--validation',action='store_true');ap.add_argument('--ras-depth',type=int,choices=(4,8),default=4);a=ap.parse_args()
    assert a.ras_depth==4 or a.variant!='bp_fold'
    variant=a.variant+('_deep' if a.ras_depth==8 else '')
    out=ROOT/('simulation/results/load_bp_'+variant);out.mkdir(parents=True,exist_ok=True)
    dest=out/('validation' if a.validation else 'performance');dest.mkdir(exist_ok=True)
    accepted=ROOT/'docs/accepted_baseline.json';sta=ROOT/'hardware/pds/report_timing/top.rtr';b=json.loads(accepted.read_text());guard={p:sha(p) for p in (accepted,sta)}
    for n,h in b['source_sha256'].items():assert sha(ROOT/n)==h,n
    overrides={}
    for name,s in generate(a.variant).items():
        if name=='nc_btb.v' and a.ras_depth==8:
            s=replace(s,'ras_mem[0:3]','ras_mem[0:7]')
            s=replace(s,'reg[1:0] ras_sp;reg[2:0] ras_count;','reg[2:0] ras_sp;reg[3:0] ras_count;')
            s=replace(s,'wire[1:0] ras_previous','wire[2:0] ras_previous')
            s=replace(s,'wire[1:0] ras_push_index','wire[2:0] ras_push_index')
            s=replace(s,'ras_count<4','ras_count<8')
        p=ROOT/'hardware/pds/source/core'/name;q=out/name
        if not q.exists() or q.read_text()!=s:q.write_text(s)
        overrides[p]=q
    rtl=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[])
    source_tb=ROOT/'simulation/tb/soc_tb.v';uart_src=ROOT/'hardware/pds/source/perips/nc_uart.v';model=ROOT/'simulation/models/pango_ram_models.v'
    image=ROOT/('sw/build/coremark_validation_1/coremark.hex' if a.validation else 'sw/build/coremark_performance_10/coremark.hex')
    inputs=rtl+[source_tb,model,image,Path(__file__).resolve()];hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    (dest/'tool_snapshot.py').write_bytes(Path(__file__).read_bytes())
    uart=out/'nc_uart_sim.v';uart.write_text(uart_src.read_text().replace('BAUD=115200','BAUD=9375000'))
    tb=out/'soc_tb_sim.v';tb.write_text(source_tb.read_text().replace('reg[1023:0]','reg[4095:0]').replace(' defparam dut.bus.uart.BAUD=9375000;',''))
    actual=[overrides.get(p,p) for p in rtl if p!=uart_src]+[uart,model,tb];prefix=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--']
    def run(cmd,name):
        with (dest/name).open('w') as f:x=subprocess.run(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=600)
        assert x.returncode==0,(name,(dest/name).read_text(errors='replace')[-3500:])
    run([*prefix,'verilator','--binary','--timing','-j','4','-Wno-fatal','-DCOREMARK_SIM','--top-module','soc_tb','--Mdir',linux(out/'obj'),*[linux(p) for p in actual]],'compile.log')
    run([*prefix,linux(out/'obj/Vsoc_tb'),f'+image={linux(image)}',f'+trace={linux(dest)}/unused.trace',f'+uart={linux(dest)}/uart.txt','+notrace=1','+limit=33000000'],'simulation.log')
    log=(dest/'simulation.log').read_text(errors='replace');u=(dest/'uart.txt').read_text();assert 'COUNTER_CHECK_PASS' in log and 'CRC validation   : PASS' in u and 'PASS cycles=' in log
    metrics={s.split(':',1)[0].strip():s.split(':',1)[1].strip() for s in u.splitlines() if ':' in s}
    ref=json.loads((ROOT/('simulation/results/coremark_validation_1_verilator_exid_final/result.json' if a.validation else 'simulation/results/coremark_performance_10_verilator_exid_aux/result.json')).read_text())
    for k in ('Retired instructions','Retired loads','Retired stores','BJP instructions','seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal'):assert metrics[k]==ref['metrics'][k],k
    for n,h in hashes.items():assert sha(ROOT/n)==h,n
    for p,h in guard.items():assert sha(p)==h,p
    result=dict(status='PASS',variant=variant,scope='Isolated full-core predictor trial, production unchanged and not adopted',metrics=metrics,
        input_sha256=hashes,override_sha256={str(p.relative_to(ROOT)):sha(q) for p,q in overrides.items()},actual_compile_sha256={str(p.relative_to(ROOT)):sha(p) for p in actual},image_sha256=sha(image))
    for name,marker in (('predictor','PREDICTOR_STATS'),('multiply','MULTIPLY_STATS')):
        m=re.search(marker+r' ([^\r\n]+)',log);assert m;result[name]={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])}
    save(dest/'result.json',result)
    if not a.validation:save(out/'result.json',result)
    print(json.dumps(dict(variant=variant,cycles=int(metrics['Stats window cycles']),ipc=int(metrics['Retired instructions'])/int(metrics['Stats window cycles']),predictor=result['predictor']),indent=2))
if __name__=='__main__':main()
