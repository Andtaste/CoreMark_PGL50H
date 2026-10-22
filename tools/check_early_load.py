"""Full-CPU regression for isolated early-load RTL, with live protocol assertions."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'simulation/scripts/run'))
from regression import differential
import regression
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--variant',default='early_load');a=ap.parse_args()
    assert a.variant in ('early_load','early_load_predecode')
    folder=ROOT/('simulation/results/load_bp_'+a.variant);out=folder/'integration_checks';out.mkdir(exist_ok=True)
    metadata=json.loads((folder/'result.json').read_text());overrides=metadata['override_sha256']
    rtl=[folder/p.name if str(p.relative_to(ROOT)) in overrides else p for p in sorted((ROOT/'hardware/pds/source/core').glob('*.v'))]
    for n,h in overrides.items():assert sha(folder/Path(n).name)==h,n
    iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe');logs=[]
    inputs=rtl+[Path(__file__).resolve(),ROOT/'simulation/research/early_load_observer.vh']
    def run(cmd,name):
        p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(out/name).write_bytes(p.stdout+p.stderr)
        assert p.returncode==0,(name,(p.stdout+p.stderr)[-4000:]);return p.stdout.decode(errors='replace')
    def asserts(cpu):
        text=(ROOT/'simulation/research/early_load_observer.vh').read_text().split(' if(dut.cpu.csr.stats.control')[0]
        text=text.replace('dut.cpu',cpu)
        return text+f'''
 if({cpu}.early_offer && {cpu}.d_req_ready) el_requests=el_requests+1;
 if({cpu}.early_offer && !{cpu}.d_req_ready) el_stall=el_stall+1;
end
always @(negedge clk) if(finish_count==1) $display("INTEGRATION_COVERAGE requests=%0d stalls=%0d",el_requests,el_stall);
'''
    source_core=ROOT/'simulation/tb/core_tb.v';core_tb=out/'core_tb.v'
    core_tb.write_text(source_core.read_text().replace('reg[1023:0]','reg[4095:0]').replace('endmodule',asserts('dut')+'\nendmodule'));inputs+=[source_core]
    run([iv,'-g2012','-s','core_tb','-o',out/'core.vvp',*rtl,core_tb],'core_compile.log')
    coverage=dict(requests=0,stalls=0)
    for name in ('directed','random_17','random_91','random_2026','prediction'):
        image=ROOT/f'simulation/results/{name}.hex';binary=image.with_suffix('.bin');inputs+=[image,binary]
        data=binary.read_bytes();data+=bytes(65536-len(data))
        for seed in (37,613):
            trace=out/f'{name}_{seed}.trace'
            text=run([vvp,out/'core.vvp',f'+image={image}',f'+trace={trace}',f'+seed={seed}'],f'{name}_{seed}.log');assert 'PASS cycles=' in text
            if name=='directed':
                causes=[int(s.split()[-1],16) for s in trace.read_text().splitlines() if s.split()[4]=='1']
                assert causes==[4,6,5,7,2,11,2,0x80000003,0x80000007,0x8000000b],causes
            else:differential(data,trace)
            m=re.search(r'INTEGRATION_COVERAGE requests=(\d+) stalls=(\d+)',text);assert m
            coverage['requests']+=int(m[1]);coverage['stalls']+=int(m[2]);logs.append(f'core {name} seed={seed} PASS')
    assert coverage['requests']>500 and coverage['stalls']>100,coverage
    socrtl=rtl+sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('perips','sys_bus','top')],[])
    source_soc=ROOT/'simulation/tb/soc_tb.v';soc_tb=out/'soc_tb.v';model=ROOT/'simulation/models/pango_ram_models.v'
    forbidden='''
reg[31:0] forbidden_load=32'hffffffff,forbidden_store=32'hffffffff;
initial begin
 if($value$plusargs("forbidden_load=%h",forbidden_load)) begin end
 if($value$plusargs("forbidden_store=%h",forbidden_store)) begin end
end
always @(posedge clk) if(rst_n && dut.cpu.d_req_valid && dut.cpu.d_req_ready &&
 (dut.cpu.selected_memory_packet[276:245]==forbidden_load || dut.cpu.selected_memory_packet[276:245]==forbidden_store))
 $fatal(1,"younger RAM read passed older access fault");
'''
    soc_tb.write_text(source_soc.read_text().replace('reg[1023:0]','reg[4095:0]').replace('endmodule',asserts('dut.cpu')+forbidden+'\nendmodule'));inputs+=[source_soc,model,*socrtl]
    run([iv,'-g2012','-s','soc_tb','-o',out/'soc.vvp',*socrtl,model,soc_tb],'soc_compile.log')
    for name in ('prediction','throughput','soc_faults','random_17','random_91','random_2026'):
        image=ROOT/f'simulation/results/{name}.hex';binary=image.with_suffix('.bin');inputs+=[image,binary]
        data=binary.read_bytes();data+=bytes(65536-len(data));trace=out/f'soc_{name}.trace'
        text=run([vvp,out/'soc.vvp',f'+image={image}',f'+trace={trace}',f'+uart={out}/unused_uart.txt'],f'soc_{name}.log');assert 'PASS cycles=' in text
        if name=='soc_faults':
            causes=[int(s.split()[-1],16) for s in trace.read_text().splitlines() if s.split()[4]=='1']
            assert causes==[5,0,0,3,1,7,0x80000007],causes
        else:differential(data,trace)
        if name=='throughput':assert int(re.search(r'max_retire_streak=\s*(\d+)',text)[1])>=200
        logs.append('soc '+name+' PASS')
    # Actual RAM reads after failed older load/store must not even reach the
    # bus. Trap recovery skips these reads; checking retirement is weaker.
    src=ROOT/'simulation/tests/soc_faults.S';text=src.read_text()
    text=text.replace(' li a5,0xbad',' li a5,0xbad\n li s5,0x10000000')
    text=text.replace(' lw a0,0(s2)\n sw a5,0(t6)',
        ' lw a0,0(s2)\nforbidden_load:\n lw a1,0(s5)\n sw a5,0(t6)')
    text=text.replace(' sw a5,0(s2)\n // Real FENCE.I',
        ' la s4,recover_store\n sw a5,0(s2)\nforbidden_store:\n lw a1,0(s5)\nrecover_store:\n // Real FENCE.I')
    special=out/'early_faults.S';special.write_text(text)
    gcc=regression.find('riscv-none-elf-gcc',Path('D:/Program Files/riscv').glob('**/riscv-none-elf-gcc.exe'))
    old_out=regression.OUT;regression.OUT=out
    try:image,_=regression.build(gcc,special,'early_faults')
    finally:regression.OUT=old_out
    nm=Path(gcc).with_name(Path(gcc).name.replace('gcc','nm'))
    symbols=run([nm,out/'early_faults.elf'],'early_faults_symbols.log')
    pcs={n:int(re.search(r'^([0-9a-f]+)\s+\S\s+'+n+r'\s*$',symbols,re.M)[1],16) for n in ('forbidden_load','forbidden_store')}
    trace=out/'early_faults.trace'
    text=run([vvp,out/'soc.vvp',f'+image={image}',f'+trace={trace}',f'+uart={out}/unused_uart.txt',*[f'+{n}={p:x}' for n,p in pcs.items()]],'early_faults.log')
    assert 'PASS cycles=' in text
    causes=[int(s.split()[-1],16) for s in trace.read_text().splitlines() if s.split()[4]=='1']
    assert causes==[5,0,0,3,1,7,0x80000007],causes
    inputs+=[src,special,image];logs.append('soc early_faults no-younger-read-after-failed-load/store PASS')
    fixtures=sorted((ROOT/'references/isa/generated').glob('*.bin'));assert len(fixtures)==47
    for fixture in fixtures:
        data=fixture.read_bytes();data+=bytes(65536-len(data));image=out/'isa.hex'
        image.write_text(''.join(f'{int.from_bytes(data[i:i+4],"little"):08x}\n' for i in range(0,65536,4)))
        text=run([vvp,out/'soc.vvp',f'+image={image}',f'+trace={out}/{fixture.stem}.trace',f'+uart={out}/unused_uart.txt','+legacy=1','+limit=100000'],fixture.stem+'.log')
        assert 'PASS cycles=' in text;inputs+=[fixture];logs.append('isa '+fixture.stem+' PASS')
    # Exact-cycle integration proof. A cold jump to each load drains older
    # instructions; NOP padding alone would leave an older ALU queue head.
    # Observe the ACTUAL selected request descriptor, including the bypass.
    cycle_observer='''
integer cycle_edge=0,cycle_fd;initial cycle_fd=$fopen("'''+(out/'cycles.trace').as_posix()+'''","w");
always @(posedge clk) if(rst_n) begin
 cycle_edge=cycle_edge+1;
 if(dut.cpu.ex_fire) $fdisplay(cycle_fd,"EX %0d %08x",cycle_edge,dut.cpu.execute_packet[276:245]);
 if(dut.cpu.d_req_valid && dut.cpu.d_req_ready) $fdisplay(cycle_fd,"REQ %0d %08x",cycle_edge,dut.cpu.selected_memory_packet[276:245]);
 if(dut.cpu.memory_done) $fdisplay(cycle_fd,"WB %0d %08x",cycle_edge,dut.cpu.memory_packet[276:245]);
end
'''
    cycle_tb=out/'cycle_soc_tb.v';cycle_tb.write_text(source_soc.read_text().replace('reg[1023:0]','reg[4095:0]').replace('endmodule',asserts('dut.cpu')+cycle_observer+'\nendmodule'))
    run([iv,'-g2012','-s','soc_tb','-o',out/'cycles.vvp',*socrtl,model,cycle_tb],'cycles_compile.log')
    code=[];labels={}
    def addi(rd,rs,imm):return ((imm&4095)<<20)|(rs<<15)|(rd<<7)|0x13
    def lw(rd,rs,imm):return ((imm&4095)<<20)|(rs<<15)|(2<<12)|(rd<<7)|3
    def sw(rs,base,imm):return ((imm>>5)<<25)|(rs<<20)|(base<<15)|(2<<12)|((imm&31)<<7)|0x23
    def barrier():code.extend([0x0080006f,0x13])
    def mark(n):labels[n]=len(code)*4
    code.extend([0x10000437,addi(9,0,37),sw(9,8,0),0x100004b7,addi(9,9,32),sw(9,8,4),addi(9,0,41),sw(9,8,32)])
    code.extend([0x13]*12);barrier();mark('alu_load');code.append(lw(5,8,0));mark('alu_consumer');code.append(addi(6,5,1))
    code.extend([0x13]*12);barrier();mark('store_load');code.append(lw(5,8,0));mark('store_consumer');code.append(sw(5,8,8))
    code.extend([0x13]*12);barrier();mark('pointer_load');code.append(lw(10,8,4));mark('pointer_consumer');code.append(lw(11,10,0));mark('chain_consumer');code.append(addi(12,11,1))
    code.extend([0x13]*12);code.extend([0x20003f37,addi(31,0,1),sw(31,30,0),0x6f])
    image=out/'cycles.hex';image.write_text('\n'.join(f'{v:08x}' for v in code)+'\n')
    text=run([vvp,out/'cycles.vvp',f'+image={image}',f'+trace={out}/cycles_retirement.trace',f'+uart={out}/unused_uart.txt'],'cycles.log');assert 'PASS cycles=' in text
    events={}
    for line in (out/'cycles.trace').read_text().splitlines():
        t,c,pc=line.split();events[t,int(pc,16)]=int(c)
    pairs=[]
    for load,consumer in (('alu_load','alu_consumer'),('store_load','store_consumer'),('pointer_load','pointer_consumer'),('pointer_consumer','chain_consumer')):
        p=labels[load];c=labels[consumer];e=events['EX',p];r=events['REQ',p];w=events['WB',p];ce=events['EX',c]
        expected=2 if load!='pointer_consumer' else 3
        assert r==e+expected-2 and w==r+1 and ce==w+1,(load,e,r,w,ce)
        pairs.append(dict(load=load,ex=e,request=r,wb=w,consumer_ex=ce,ex_bubbles=ce-e-1))
    # Same binary on accepted RTL confirms the one-edge improvement.
    base_observer=cycle_observer.replace('selected_memory_packet','mem_packet').replace('cycles.trace','baseline_cycles.trace')
    base_tb=out/'base_soc_tb.v';base_tb.write_text(source_soc.read_text().replace('reg[1023:0]','reg[4095:0]').replace('endmodule',base_observer+'\nendmodule'))
    basertl=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[])
    run([iv,'-g2012','-s','soc_tb','-o',out/'baseline_cycles.vvp',*basertl,model,base_tb],'baseline_cycles_compile.log')
    text=run([vvp,out/'baseline_cycles.vvp',f'+image={image}',f'+trace={out}/baseline_cycles_retirement.trace',f'+uart={out}/unused_uart.txt'],'baseline_cycles.log');assert 'PASS cycles=' in text
    base_events={}
    for line in (out/'baseline_cycles.trace').read_text().splitlines():
        t,c,pc=line.split();base_events[t,int(pc,16)]=int(c)
    for pair,consumer in zip(pairs,('alu_consumer','store_consumer','pointer_consumer','chain_consumer')):
        p=labels[pair['load']];c=labels[consumer];e=base_events['EX',p]
        assert base_events['REQ',p]==e+1 and base_events['WB',p]==e+2 and base_events['EX',c]==e+3
        pair['baseline_ex_bubbles']=2
    # Compare all retired tuples until successful tohost, irrespective of
    # the different post-completion spin counts in the two runs.
    def prefix(path):
        rows=path.read_text().splitlines();return rows[:next(i for i,s in enumerate(rows) if int(s.split()[0],16)==(len(code)-2)*4)+1]
    assert prefix(out/'cycles_retirement.trace')==prefix(out/'baseline_cycles_retirement.trace')
    result=dict(status='PASS',scope='10 variable-latency core + 7 SoC differential/fault/FENCE/throughput + 47 ISA + integrated cycle proof',
        tests=logs,core_random_delay_coverage=coverage,directed_pairs=pairs,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs})
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('tests','input_sha256')},indent=2))
if __name__=='__main__':main()
