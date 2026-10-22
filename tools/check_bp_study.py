"""Independent unit model plus full core/SoC/ISA regression for BP trials."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'simulation/scripts/run'))
import regression
from regression import differential
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True,choices=('bp_fold','bp_ras','bp_combo'));ap.add_argument('--unit-only',action='store_true');a=ap.parse_args()
    folder=ROOT/('simulation/results/load_bp_'+a.variant);out=folder/'checks';out.mkdir(exist_ok=True)
    meta=json.loads((folder/'result.json').read_text());override=meta['override_sha256']
    rtl=[folder/p.name if str(p.relative_to(ROOT)) in override else p for p in sorted((ROOT/'hardware/pds/source/core').glob('*.v'))]
    for n,h in override.items():assert sha(folder/Path(n).name)==h,n
    inputs=rtl+[Path(__file__).resolve()];iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe');logs=[]
    def run(cmd,name):
        p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(out/name).write_bytes(p.stdout+p.stderr)
        assert p.returncode==0,(name,(p.stdout+p.stderr)[-3500:]);return p.stdout.decode(errors='replace')
    ras=a.variant!='bp_fold';folded=a.variant!='bp_ras';unit=ROOT/'simulation/research/bp_study_tb.v';inputs+=[unit]
    flags=['-DHAS_STUDY_RAS'] if ras else []
    run([iv,'-g2012',*flags,'-s','bp_study_tb',f'-Pbp_study_tb.FOLDED={int(folded)}',f'-Pbp_study_tb.RAS={int(ras)}','-o',out/'unit.vvp',folder/'nc_btb.v',unit],'unit_compile.log')
    text=run([vvp,out/'unit.vvp'],'unit.log');assert 'PASS study predictor updates=20000' in text;logs.append(text.strip())
    if a.unit_only:print(text);return
    source_core=ROOT/'simulation/tb/core_tb.v';source_soc=ROOT/'simulation/tb/soc_tb.v';model=ROOT/'simulation/models/pango_ram_models.v'
    inputs+=[source_core,source_soc,model]
    coverage=''
    if ras:coverage='''
integer train_pushes=0,train_pops=0,ras_lookups=0;
always @(posedge clk) if(rst_n) begin
 if(dut.bp_update_valid && dut.bp_update_branch) begin
  if(dut.bp_update_call) train_pushes=train_pushes+1;
  if(dut.bp_update_pop) train_pops=train_pops+1;
 end
 if(dut.fetch.prepare && dut.fetch.predictor.btb.hit && dut.fetch.predictor.btb.use_ras) ras_lookups=ras_lookups+1;
end
always @(negedge clk) if(finish_count==1) $display("RAS_CORE pushes=%0d pops=%0d lookups=%0d",train_pushes,train_pops,ras_lookups);
'''
    core_tb=out/'core_tb.v';core_tb.write_text(source_core.read_text().replace('reg[1023:0]','reg[4095:0]').replace('endmodule',coverage+'\nendmodule'))
    run([iv,'-g2012','-s','core_tb','-o',out/'core.vvp',*rtl,core_tb],'core_compile.log')
    for name in ('directed','random_17','random_91','random_2026','prediction'):
        image=ROOT/f'simulation/results/{name}.hex';binary=image.with_suffix('.bin');inputs+=[image,binary];data=binary.read_bytes();data+=bytes(65536-len(data))
        for seed in (37,613):
            trace=out/f'{name}_{seed}.trace';text=run([vvp,out/'core.vvp',f'+image={image}',f'+trace={trace}',f'+seed={seed}'],f'{name}_{seed}.log');assert 'PASS cycles=' in text
            if name=='directed':
                causes=[int(s.split()[-1],16) for s in trace.read_text().splitlines() if s.split()[4]=='1'];assert causes==[4,6,5,7,2,11,2,0x80000003,0x80000007,0x8000000b],causes
            else:differential(data,trace)
            logs.append(f'core {name} seed={seed} PASS')
    socrtl=rtl+sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('perips','sys_bus','top')],[]);inputs+=socrtl
    soc_tb=out/'soc_tb.v';soc_tb.write_text(source_soc.read_text().replace('reg[1023:0]','reg[4095:0]'))
    run([iv,'-g2012','-s','soc_tb','-o',out/'soc.vvp',*socrtl,model,soc_tb],'soc_compile.log')
    for name in ('prediction','throughput','soc_faults','random_17','random_91','random_2026'):
        image=ROOT/f'simulation/results/{name}.hex';binary=image.with_suffix('.bin');inputs+=[image,binary];data=binary.read_bytes();data+=bytes(65536-len(data));trace=out/f'soc_{name}.trace'
        text=run([vvp,out/'soc.vvp',f'+image={image}',f'+trace={trace}',f'+uart={out}/unused_uart.txt'],f'soc_{name}.log');assert 'PASS cycles=' in text
        if name=='soc_faults':
            causes=[int(s.split()[-1],16) for s in trace.read_text().splitlines() if s.split()[4]=='1'];assert causes==[5,0,0,3,1,7,0x80000007],causes
        else:differential(data,trace)
        if name=='throughput':assert int(re.search(r'max_retire_streak=\s*(\d+)',text)[1])>=200
        logs.append('soc '+name+' PASS')
    src=ROOT/'simulation/research/bp_ras_calls.S';gcc=regression.find('riscv-none-elf-gcc',Path('D:/Program Files/riscv').glob('**/riscv-none-elf-gcc.exe'));previous=regression.OUT;regression.OUT=out
    try:image,data=regression.build(gcc,src,'ras_calls')
    finally:regression.OUT=previous
    inputs+=[src,image];ras_coverage=[]
    for seed in (37,613):
        trace=out/f'calls_{seed}.trace';text=run([vvp,out/'core.vvp',f'+image={image}',f'+trace={trace}',f'+seed={seed}'],f'calls_{seed}.log');assert 'PASS cycles=' in text;differential(data,trace)
        if ras:
            m=re.search(r'RAS_CORE pushes=(\d+) pops=(\d+) lookups=(\d+)',text);assert m and int(m[1])>100 and int(m[2])>100 and int(m[3])>30,m
            ras_coverage.append(dict(seed=seed,pushes=int(m[1]),pops=int(m[2]),lookups=int(m[3])))
        logs.append(f'core nested/x5/coroutine calls seed={seed} PASS')
    trace=out/'calls_soc.trace';text=run([vvp,out/'soc.vvp',f'+image={image}',f'+trace={trace}',f'+uart={out}/unused_uart.txt'],'calls_soc.log');assert 'PASS cycles=' in text;differential(data,trace);logs.append('soc nested/x5/coroutine calls PASS')
    fixtures=sorted((ROOT/'references/isa/generated').glob('*.bin'));assert len(fixtures)==47
    for fixture in fixtures:
        data=fixture.read_bytes();data+=bytes(65536-len(data));image=out/'isa.hex';image.write_text(''.join(f'{int.from_bytes(data[i:i+4],"little"):08x}\n' for i in range(0,65536,4)))
        text=run([vvp,out/'soc.vvp',f'+image={image}',f'+trace={out}/{fixture.stem}.trace',f'+uart={out}/unused_uart.txt','+legacy=1','+limit=100000'],fixture.stem+'.log');assert 'PASS cycles=' in text
        inputs+=[fixture];logs.append('isa '+fixture.stem+' PASS')
    x=dict(status='PASS',variant=a.variant,scope='20k independent predictor unit + 10 delayed core + 6 SoC + 3 call/return + 47 ISA fixtures',tests=logs,ras_coverage=ras_coverage,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs})
    (out/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({k:v for k,v in x.items() if k not in ('tests','input_sha256')},indent=2))
if __name__=='__main__':main()
