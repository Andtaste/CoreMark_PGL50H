"""Build fresh firmware, simulate variable latency, compare retirements to an
independent RV32IM interpreter. Tools may be supplied explicitly or discovered.
No production files outside new_core are modified.
"""
from pathlib import Path
import argparse, json, random, shutil, subprocess, re
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'simulation/results'
def find(name, candidates):
    found=shutil.which(name)
    if found:return found
    for p in candidates:
        if Path(p).is_file():return str(p)
    raise RuntimeError(f'{name} missing; use command-line tool override')
def run(cmd,log):
    p=subprocess.run(list(map(str,cmd)),cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
    log.write_bytes(p.stdout)
    if p.returncode:raise RuntimeError(log.read_text(errors='replace')[-5000:])
    return p.stdout.decode(errors='replace')
def build(gcc, source, name):
    elf=OUT/(name+'.elf'); binary=OUT/(name+'.bin'); image=OUT/(name+'.hex')
    run([gcc,'-march=rv32im_zicsr_zifencei','-mabi=ilp32','-nostdlib','-mno-relax',
         '-Wl,--build-id=none','-T',ROOT/'sw/link.lds',source,'-o',elf],OUT/(name+'_build.log'))
    run([Path(gcc).with_name(Path(gcc).name.replace('gcc','objcopy')),'-O','binary',elf,binary],OUT/(name+'_objcopy.log'))
    data=binary.read_bytes(); assert len(data)<=65536
    data+=bytes(65536-len(data))
    image.write_text(''.join(f'{int.from_bytes(data[i:i+4],"little"):08x}\n' for i in range(0,65536,4)))
    return image,data
def random_source(seed):
    rng=random.Random(seed); lines=['.section .text.start','.globl _start','_start:']
    for r in range(1,32):lines.append(f'li x{r},0x{rng.getrandbits(32):08x}')
    lines+=['li x28,0x10000000']
    for k in range(1200):
        rd,a,b=[rng.randrange(1,26) for _ in range(3)];mode=rng.randrange(7)
        if mode<=1:
            op=rng.choice('add sub sll slt sltu xor srl sra or and mul mulh mulhsu mulhu div divu rem remu'.split())
            lines.append(f'{op} x{rd},x{a},x{b}')
        elif mode==2:
            op=rng.choice('addi slti sltiu xori ori andi'.split());lines.append(f'{op} x{rd},x{a},{rng.randrange(-2048,2048)}')
        elif mode==3:
            op=rng.choice('slli srli srai'.split());lines.append(f'{op} x{rd},x{a},{rng.randrange(32)}')
        elif mode==4:
            op=rng.choice('lb lbu lh lhu lw sb sh sw'.split());align=4 if op in ('lw','sw') else 2 if op in ('lh','lhu','sh') else 1
            lines.append(f'{op} x{rd},{rng.randrange(64)*align}(x28)')
        elif mode==5:
            op=rng.choice('beq bne blt bge bltu bgeu'.split())
            lines +=[f'{op} x{a},x{b},L{k}',f'addi x{rd},x{rd},1',f'L{k}:']
        else: lines +=[f'jal x{rd},L{k}',f'addi x{rd},x{rd},7',f'L{k}:']
    lines+=['li x28,0x20003000','li x29,1','sw x29,0(x28)','tail: j tail']
    return '\n'.join(lines)+'\n'
def s(v,b=32):return (v & ((1<<(b-1))-1))-(v & (1<<(b-1)))
def differential(data,trace):
    regs=[0]*32;pc=0;memory={i:b for i,b in enumerate(data)};n=0;finished=False
    for line in trace.read_text().splitlines():
        parts=line.split();tp,insn=int(parts[0],16),int(parts[1],16);rdgot=int(parts[2]);val=int(parts[3],16)
        assert int(parts[4])==0, f'unexpected trap {line}'
        assert tp==pc,f'PC {tp:x} expected {pc:x}'
        assert insn==sum(memory.get(pc+i,0)<<(8*i) for i in range(4)),f'instruction mismatch {pc:x}'
        op=insn&127;rd=(insn>>7)&31;f3=(insn>>12)&7;a=regs[(insn>>15)&31];b=regs[(insn>>20)&31];f7=insn>>25
        imm=s(insn>>20,12);nxt=(pc+4)&0xffffffff;value=0;write=False
        if op in (0x37,0x17):write=True;value=(insn&0xfffff000)+(pc if op==0x17 else 0)
        elif op in (0x13,0x33):
            write=True;rhs=(imm&0xffffffff) if op==0x13 else b;shift=rhs&31
            if op==0x33 and f7==1:
                if f3<4:
                    aa=s(a) if f3 in (1,2) else a;bb=s(b) if f3==1 else b
                    value=aa*bb;value=value if f3==0 else value>>32
                else:
                    aa=s(a) if f3 in (4,6) else a;bb=s(b) if f3 in (4,6) else b
                    q=-1 if bb==0 else (abs(aa)//abs(bb))*(-1 if (aa<0)^(bb<0) else 1)
                    value=q if f3<6 else aa if bb==0 else aa-q*bb
            elif f3==0:value=a-rhs if op==0x33 and f7==32 else a+rhs
            elif f3==1:value=a<<shift
            elif f3==2:value=int(s(a)<s(rhs))
            elif f3==3:value=int(a<rhs)
            elif f3==4:value=a^rhs
            elif f3==5:value=s(a)>>shift if (insn>>30)&1 else a>>shift
            elif f3==6:value=a|rhs
            else:value=a&rhs
        elif op==0x63:
            offset=s(((insn>>31)<<12)|(((insn>>7)&1)<<11)|(((insn>>25)&63)<<5)|(((insn>>8)&15)<<1),13)
            cond={0:a==b,1:a!=b,4:s(a)<s(b),5:s(a)>=s(b),6:a<b,7:a>=b}[f3]
            if cond:nxt=(pc+offset)&0xffffffff
        elif op==0x6f:
            offset=s(((insn>>31)<<20)|(((insn>>12)&255)<<12)|(((insn>>20)&1)<<11)|(((insn>>21)&1023)<<1),21)
            write=True;value=pc+4;nxt=(pc+offset)&0xffffffff
        elif op==0x67:write=True;value=pc+4;nxt=(a+imm)&0xfffffffe
        elif op in (3,0x23):
            if op==0x23:imm=s(((insn>>25)<<5)|((insn>>7)&31),12)
            addr=(a+imm)&0xffffffff;size=1<<(f3&3)
            if op==3:
                write=True;value=sum(memory.get(addr+i,0)<<(8*i) for i in range(size))
                if f3<4:value=s(value,8*size)
            else:
                if addr==0x20003000:assert b==1;finished=True
                for i in range(size):memory[addr+i]=(b>>(8*i))&255
        elif op==0x0f:pass # FENCE/FENCE.I: this single-hart reference has coherent instruction bytes.
        else:raise AssertionError(f'unsupported instruction {insn:08x}')
        expected_rd=rd if write else 0;value&=0xffffffff
        assert rdgot==expected_rd and val==(value if expected_rd else 0),f'REG at {pc:x}: got x{rdgot}={val:x}, expected x{expected_rd}={value:x}'
        if write and rd:regs[rd]=value
        pc=nxt;n+=1
    assert finished,'missing retired finish store'
    return n
def main():
    p=argparse.ArgumentParser();p.add_argument('--iverilog');p.add_argument('--vvp');p.add_argument('--gcc');a=p.parse_args()
    iv=a.iverilog or find('iverilog',[ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe'])
    vvp=a.vvp or find('vvp',[ROOT.parent/'tmp/iverilog-portable/bin/vvp.exe'])
    gcc=a.gcc or find('riscv-none-elf-gcc',Path('D:/Program Files/riscv').glob('**/riscv-none-elf-gcc.exe'))
    OUT.mkdir(parents=True,exist_ok=True)
    rtl=sorted((ROOT/'hardware/pds/source/core').glob('*.v'))
    run([iv,'-g2012','-s','stats_tb','-o',OUT/'stats.vvp',ROOT/'hardware/pds/source/core/nc_stats.v',
         ROOT/'simulation/tb/stats_tb.v'],OUT/'stats_compile.log')
    stats=run([vvp,OUT/'stats.vvp'],OUT/'stats.log')
    assert 'PASS stats' in stats,stats
    run([iv,'-g2012','-s','dependency_priority_tb','-o',OUT/'dependency_priority.vvp',*rtl,
         ROOT/'simulation/tb/dependency_priority_tb.v'],OUT/'dependency_priority_compile.log')
    priority=run([vvp,OUT/'dependency_priority.vvp'],OUT/'dependency_priority.log')
    assert 'PASS dependency priority checks=4088' in priority,priority
    run([iv,'-g2012','-Wall','-s','core_tb','-o',OUT/'core.vvp',*rtl,ROOT/'simulation/tb/core_tb.v'],OUT/'compile.log')
    results=[]
    for name,src in [('directed',ROOT/'simulation/tests/directed.S')]+[(f'random_{seed}',None) for seed in (17,91,2026)]:
        if src is None:
            src=OUT/(name+'.S');src.write_text(random_source(int(name.split('_')[1])))
        image,data=build(gcc,src,name)
        for delay_seed in (37,613):
            trace=OUT/f'{name}_{delay_seed}.trace'
            output=run([vvp,OUT/'core.vvp',f'+image={image}',f'+trace={trace}',f'+seed={delay_seed}'],OUT/f'{name}_{delay_seed}.log')
            assert 'PASS cycles=' in output,output
            item={'test':name,'delay_seed':delay_seed,'status':'PASS','summary':output.strip()}
            if name.startswith('random'):item['differential_retirements']=differential(data,trace)
            else:
                causes=[int(x.split()[5],16) for x in trace.read_text().splitlines() if int(x.split()[4])]
                assert causes==[4,6,5,7,2,11,2,0x80000003,0x80000007,0x8000000b],causes
                item['trap_causes']=causes
            results.append(item);print(name,delay_seed,'PASS',flush=True)
    socrtl=rtl+sorted((ROOT/'hardware/pds/source/perips').glob('*.v'))+sorted((ROOT/'hardware/pds/source/sys_bus').glob('*.v'))+sorted((ROOT/'hardware/pds/source/top').glob('*.v'))
    run([iv,'-g2012','-Wall','-s','soc_tb','-o',OUT/'soc.vvp',*socrtl,ROOT/'simulation/models/pango_ram_models.v',ROOT/'simulation/tb/soc_tb.v'],OUT/'soc_compile.log')
    for name in ('throughput','soc_faults','random_17','random_91','random_2026'):
        if name in ('throughput','soc_faults'):image,data=build(gcc,ROOT/f'simulation/tests/{name}.S',name)
        else:
            image=OUT/(name+'.hex');data=b''.join(int(v,16).to_bytes(4,'little') for v in image.read_text().split())
        trace=OUT/f'soc_{name}.trace'
        output=run([vvp,OUT/'soc.vvp',f'+image={image}',f'+trace={trace}'],OUT/f'soc_{name}.log')
        assert 'PASS cycles=' in output,output
        compared=0 if name=='soc_faults' else differential(data,trace)
        if name=='soc_faults':
            causes=[int(x.split()[5],16) for x in trace.read_text().splitlines() if int(x.split()[4])]
            assert causes==[5,0,0,3,1,7,0x80000007],causes
        if name=='throughput':assert int(re.search(r'max_retire_streak=\s*(\d+)',output)[1])>=200,output
        results.append({'test':'soc_'+name,'status':'PASS','differential_retirements':compared,'summary':output.strip()})
        print('soc',name,'PASS',flush=True)
    demo=ROOT/'sw/build/demo.hex'
    if demo.exists():
        trace=OUT/'soc_demo.trace'
        output=run([vvp,OUT/'soc.vvp',f'+image={demo}',f'+trace={trace}',f'+uart={trace}.uart'],OUT/'soc_demo.log')
        assert 'PASS cycles=' in output,output
        assert trace.with_suffix('.trace.uart').read_bytes()==b'new_core RV32IM PASS\r\n'
        results.append({'test':'soc_demo_uart','status':'PASS','summary':output.strip(),'uart':'new_core RV32IM PASS'})
        print('soc demo UART PASS',flush=True)
    (OUT/'regression.json').write_text(json.dumps({'scope':'core functional + independent RV32IM random differential, not timing signoff','results':results},indent=2))
if __name__=='__main__':main()
