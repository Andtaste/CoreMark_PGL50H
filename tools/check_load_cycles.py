"""Cycle feasibility only. Accepted CPU and firmware are never changed.

Part A executes real production RTL with a directed RAM image and CoreMark.
Part B tests a proposed early descriptor using production MEM/operand slices.
The slice omits ID AGU timing and core-wide authorization and is not signoff.
"""
from pathlib import Path
import hashlib,json,re,subprocess,shutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'simulation/results/load_cycle_structure'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def linux(p):
    p=Path(p).resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    accepted=ROOT/'docs/accepted_baseline.json';sta=ROOT/'hardware/pds/report_timing/top.rtr'
    baseline=json.loads(accepted.read_text());guard={p:sha(p) for p in [accepted,sta,*[ROOT/n for n in baseline['source_sha256']]]}
    for n,h in baseline['source_sha256'].items():assert sha(ROOT/n)==h,n
    rtl=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[])
    model=ROOT/'simulation/models/pango_ram_models.v';source_tb=ROOT/'simulation/tb/soc_tb.v'
    observer=ROOT/'simulation/research/load_cycle_observer.vh';slice_tb=ROOT/'simulation/research/load_cycle_slice_tb.v'
    turnover_tbs=[ROOT/'simulation/tb'/n for n in ('memory_turnover_tb.v','memory_overlap_tb.v')]
    inputs=rtl+[model,source_tb,observer,slice_tb,*turnover_tbs,Path(__file__).resolve()]
    initial_hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    def run(cmd,name,timeout=300):
        p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=timeout)
        (OUT/name).write_bytes(p.stdout+p.stderr)
        assert p.returncode==0,(name,(p.stdout+p.stderr)[-3000:]);return p.stdout.decode(errors='replace')
    iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
    slice_rtl=[ROOT/'hardware/pds/source/core'/n for n in ('nc_memory.v','nc_operands.v')]
    run([iv,'-g2012','-s','load_cycle_slice_tb','-o',OUT/'slice.vvp',*slice_rtl,slice_tb],'slice_compile.log')
    slice_log=run([vvp,OUT/'slice.vvp',f'+vcd={OUT}/slice.vcd'],'slice.log');assert 'PASS load cycle contract cases=13' in slice_log
    # Re-run a second simulator to catch event ordering/width differences.
    prefix=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--']
    run([*prefix,'verilator','--binary','--timing','-j','4','-Wno-fatal','--top-module','load_cycle_slice_tb','--Mdir',linux(OUT/'slice_obj'),*[linux(p) for p in slice_rtl+[slice_tb]]],'slice_verilator_compile.log')
    vl=run([*prefix,linux(OUT/'slice_obj/Vload_cycle_slice_tb')],'slice_verilator.log')
    assert 'PASS load cycle contract cases=13' in vl
    assert re.findall(r'SLICE_PASS[^\r\n]+',slice_log)==re.findall(r'SLICE_PASS[^\r\n]+',vl)
    mem_checks={}
    for unit in turnover_tbs:
        run([iv,'-g2012','-s',unit.stem,'-o',OUT/(unit.stem+'.vvp'),slice_rtl[0],unit],unit.stem+'_compile.log')
        text=run([vvp,OUT/(unit.stem+'.vvp')],unit.stem+'.log');assert 'PASS' in text
        mem_checks[unit.stem]=text.strip()
    uart_src=ROOT/'hardware/pds/source/perips/nc_uart.v';uart=OUT/'nc_uart_sim.v'
    uart.write_text(uart_src.read_text().replace('BAUD=115200','BAUD=9375000'))
    tb=OUT/'soc_tb_sim.v';tb.write_text(source_tb.read_text().replace(' defparam dut.bus.uart.BAUD=9375000;','').replace('endmodule',observer.read_text()+'\nendmodule'))
    actual=[p for p in rtl if p!=uart_src]+[uart,model,tb]
    run([*prefix,'verilator','--binary','--timing','-j','4','-Wno-fatal','-DCOREMARK_SIM','--top-module','soc_tb','--Mdir',linux(OUT/'obj'),*[linux(p) for p in actual]],'compile.log')
    code=[];labels={}
    def emit(x):code.append(x)
    def nop(n):code.extend([0x13]*n)
    def addi(rd,rs,imm):return ((imm&4095)<<20)|(rs<<15)|(rd<<7)|0x13
    def lw(rd,rs,imm):return ((imm&4095)<<20)|(rs<<15)|(2<<12)|(rd<<7)|3
    def sw(rs,base,imm):return ((imm>>5)<<25)|(rs<<20)|(base<<15)|(2<<12)|((imm&31)<<7)|0x23
    def mark(name):labels[name]=len(code)*4
    emit(0x10000437);emit(addi(9,0,37));emit(sw(9,8,0));nop(16)
    mark('alu_load');emit(lw(5,8,0));mark('alu_consumer');emit(addi(6,5,1));nop(12)
    mark('store_load');emit(lw(5,8,0));mark('store_consumer');emit(sw(5,8,8));nop(12)
    emit(0x100004b7);emit(addi(9,9,32));emit(sw(9,8,4));emit(addi(9,0,41));emit(sw(9,8,32));nop(16)
    mark('pointer_load');emit(lw(10,8,4));mark('pointer_consumer');emit(lw(11,10,0));mark('chain_consumer');emit(addi(12,11,1));nop(12)
    emit(0x20003f37);emit(addi(31,0,1));emit(sw(31,30,0));emit(0x6f)
    image=OUT/'directed.hex';image.write_text('\n'.join(f'{x:08x}' for x in code)+'\n')
    def soc(image,name,verbose,notrace):
        folder=OUT/name;folder.mkdir(exist_ok=True)
        log=run([*prefix,linux(OUT/'obj/Vsoc_tb'),f'+image={linux(image)}',f'+trace={linux(folder)}/retirement.trace',f'+cycletrace={linux(folder)}/cycles.trace',f'+cycleverbose={verbose}',f'+uart={linux(folder)}/uart.txt',f'+notrace={notrace}','+limit=33000000'],name+'.log',600)
        assert 'PASS cycles=' in log;return folder,log
    folder,log=soc(image,'directed',1,0)
    events={}
    for line in (folder/'cycles.trace').read_text().splitlines():
        t,edge,pc,*rest=line.split();events[(t,int(pc,16))]=int(edge)
    pairs=[]
    for load,consumer in (('alu_load','alu_consumer'),('store_load','store_consumer'),('pointer_load','pointer_consumer'),('pointer_consumer','chain_consumer')):
        e=events['EX',labels[load]];r=events['REQ',labels[load]];w=events['WB_CAPTURE',labels[load]];c=events['EX',labels[consumer]]
        assert r==e+1 and w==r+1 and c==w+1,(load,e,r,w,c)
        pairs.append(dict(load=load,consumer=consumer,load_pc=labels[load],consumer_pc=labels[consumer],ex=e,request=r,wb_capture=w,consumer_ex=c,ex_bubbles=c-e-1))
    retired=[s.split() for s in (folder/'retirement.trace').read_text().splitlines()]
    assert all(int(s[4])==0 for s in retired),'directed trap'
    for name,expected in (('alu_consumer',38),('pointer_load',0x10000020),('pointer_consumer',41),('chain_consumer',42)):
        row=next(s for s in retired if int(s[0],16)==labels[name]);assert int(row[3],16)==expected,(name,row)
    # Same accepted image, same counters; observer cannot change performance.
    cm_image=ROOT/'sw/build/coremark_performance_10/coremark.hex';cm,log=soc(cm_image,'coremark',0,1)
    assert 'COUNTER_CHECK_PASS cycles=3605011 retired=2808261 loads=548709 stores=143410' in log
    assert 'CRC validation   : PASS' in (cm/'uart.txt').read_text()
    match=re.search(r'LOAD_CYCLE_PROFILE ([^\r\n]+)',log);assert match
    profile={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',match[1])}
    assert profile['loads']==548709
    for p,h in guard.items():assert sha(p)==h,p
    for n,h in initial_hashes.items():assert sha(ROOT/n)==h,n
    result=dict(status='PASS',scope='Cycle feasibility only; no candidate integrated or synthesized',
        production_unchanged=True,directed_pairs=pairs,slice_cases=13,slice_simulators=['Icarus','Verilator'],
        coremark_cycles=3605011,coremark_retired=2808261,profile=profile,
        production_memory_contract_checks=mem_checks,
        limits=['ID RF-to-AGU adder timing is NOT modeled by the slice.',
                'Older ordering authorization is an EXTERNAL REGISTERED contract in the slice, not proven core integration.',
                'Strict eligible coverage is a subset, not an upper bound or predicted IPC gain.',
                'No additional PDS run; resource and Fmax numbers remain those of accepted production.'],
        input_sha256=initial_hashes,accepted_sha256=sha(accepted),production_sta_sha256=sha(sta),image_sha256=sha(cm_image))
    save(OUT/'result.json',result)
    archive=ROOT/'docs/load_cycle_structure';archive.mkdir(parents=True,exist_ok=True)
    for p in inputs:
        q=archive/'source'/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
    for p in [accepted,cm_image]:shutil.copyfile(p,archive/p.name)
    for name in ('result.json','slice.log','slice_compile.log','slice_verilator.log','slice_verilator_compile.log','slice.vcd','compile.log','directed.log','coremark.log','directed.hex','soc_tb_sim.v','nc_uart_sim.v','memory_turnover_tb.log','memory_overlap_tb.log'):
        shutil.copyfile(OUT/name,archive/name)
    for name in ('directed','coremark'):
        (archive/name).mkdir(exist_ok=True)
        for p in (OUT/name).glob('*'):shutil.copyfile(p,archive/name/p.name)
    save(archive/'manifest.json',{str(p.relative_to(archive)):sha(p) for p in sorted(archive.rglob('*')) if p.is_file() and p.name!='manifest.json'})
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
