"""Inject a bus error into a truly early RAM load in the full core."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'simulation/scripts/run'))
import regression
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--variant',default='early_load');a=ap.parse_args()
    assert a.variant in ('early_load','early_load_predecode')
    folder=ROOT/('simulation/results/load_bp_'+a.variant);out=folder/'injected_fault';out.mkdir(exist_ok=True)
    result=json.loads((folder/'result.json').read_text());overrides=result['override_sha256']
    rtl=[folder/p.name if str(p.relative_to(ROOT)) in overrides else p for p in sorted((ROOT/'hardware/pds/source/core').glob('*.v'))]
    gcc=regression.find('riscv-none-elf-gcc',Path('D:/Program Files/riscv').glob('**/riscv-none-elf-gcc.exe'))
    src=ROOT/'simulation/research/early_load_fault.S';old_out=regression.OUT;regression.OUT=out
    try:image,_=regression.build(gcc,src,'early_ram_fault')
    finally:regression.OUT=old_out
    def run(cmd,name):
        p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(out/name).write_bytes(p.stdout+p.stderr)
        assert p.returncode==0,(name,(p.stdout+p.stderr)[-3000:]);return p.stdout.decode(errors='replace')
    symbols=run([Path(gcc).with_name(Path(gcc).name.replace('gcc','nm')),out/'early_ram_fault.elf'],'symbols.log')
    pc=int(re.search(r'^([0-9a-f]+)\s+\S\s+faulting_load\s*$',symbols,re.M)[1],16)
    source_tb=ROOT/'simulation/tb/core_tb.v';observer=ROOT/'simulation/research/early_load_observer.vh'
    obs=observer.read_text().split(' if(dut.cpu.csr.stats.control')[0].replace('dut.cpu','dut')+'\nend\n'
    obs+=f'''
integer injected_early_reads=0;
always @(negedge clk) if(finish_count==1) $display("EARLY_INJECTED reads=%0d",injected_early_reads);
always @(posedge clk) if(rst_n && dv && dr && dut.selected_memory_packet[276:245]==32'h{pc+8:08x})
 $fatal(1,"younger load requested after early RAM bus fault");
'''
    text=source_tb.read_text().replace('reg[1023:0]','reg[4095:0]').replace('if(index(da)>=0) begin',
        '''if(index(da)>=0) begin
    if(!dwrite && da==32'h10000040) begin
     derr<=1;
     if(dut.early_offer) injected_early_reads<=injected_early_reads+1;
    end''').replace('endmodule',obs+'\nendmodule')
    tb=out/'core_tb.v';tb.write_text(text)
    iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe')
    run([iv,'-g2012','-s','core_tb','-o',out/'test.vvp',*rtl,tb],'compile.log')
    tests=[]
    for seed in (37,613):
        trace=out/f'{seed}.trace';text=run([vvp,out/'test.vvp',f'+image={image}',f'+trace={trace}',f'+seed={seed}'],f'{seed}.log')
        assert 'PASS cycles=' in text and 'EARLY_INJECTED reads=1' in text,text
        traps=[s.split() for s in trace.read_text().splitlines() if s.split()[4]=='1']
        assert len(traps)==1 and int(traps[0][0],16)==pc and int(traps[0][-1],16)==5,traps
        tests.append(dict(seed=seed,status='PASS',accepted_early_read_errors=1,trap_pc=pc,cause=5))
    inputs=rtl+[source_tb,observer,src,tb,image,Path(__file__).resolve()]
    x=dict(status='PASS',scope='Full-core variable-latency early-RAM error injection, mtval/mepc recovery and no younger bus request',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs})
    (out/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({k:v for k,v in x.items() if k!='input_sha256'},indent=2))
if __name__=='__main__':main()
