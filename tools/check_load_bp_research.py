"""Pilot functional checks for isolated research, not production signoff."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'simulation/scripts/run'))
from regression import differential
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args()
    folder=ROOT/('simulation/results/load_bp_'+a.variant);result=json.loads((folder/'result.json').read_text());out=folder/'checks';out.mkdir(exist_ok=True)
    override=result['override_sha256'];rtl=[]
    for p in sorted((ROOT/'hardware/pds/source/core').glob('*.v')):
        rtl.append(folder/p.name if str(p.relative_to(ROOT)) in override else p)
    iv=str(ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe');vvp=str(ROOT.parent/'tmp/iverilog-portable/bin/vvp.exe');logs=[]
    inputs=rtl+[ROOT/'simulation/tb/core_tb.v',ROOT/'simulation/tb/soc_tb.v',ROOT/'simulation/models/pango_ram_models.v',Path(__file__).resolve()]
    def run(cmd,name):
        p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(out/name).write_bytes(p.stdout+p.stderr);assert p.returncode==0,(name,(p.stdout+p.stderr)[-2000:]);return p.stdout.decode(errors='replace')
    if (folder/'nc_btb.v').exists():
        tb=ROOT/'simulation/research/btb_two_way_tb.v';inputs+=[tb]
        run([iv,'-g2012','-s','btb_two_way_tb',f'-Pbtb_two_way_tb.HASH={int(a.variant.endswith("_xor"))}','-o',out/'btb.vvp',folder/'nc_btb.v',tb],'btb_compile.log')
        text=run([vvp,out/'btb.vvp'],'btb.log');assert 'PASS two-way BTB updates=20000' in text;logs.append(text.strip())
    run([iv,'-g2012','-s','core_tb','-o',out/'core.vvp',*rtl,ROOT/'simulation/tb/core_tb.v'],'core_compile.log')
    for name in ('directed','random_17','random_91','random_2026','prediction'):
        image=ROOT/f'simulation/results/{name}.hex';binary=ROOT/f'simulation/results/{name}.bin';inputs+=[image,binary]
        data=binary.read_bytes();data+=bytes(65536-len(data))
        for seed in (37,613):
            trace=out/f'{name}_{seed}.trace';text=run([vvp,out/'core.vvp',f'+image={image}',f'+trace={trace}',f'+seed={seed}'],f'{name}_{seed}.log');assert 'PASS cycles=' in text
            if name=='directed':
                causes=[int(s.split()[-1],16) for s in trace.read_text().splitlines() if s.split()[4]=='1']
                assert causes==[4,6,5,7,2,11,2,0x80000003,0x80000007,0x8000000b],causes
            else:differential(data,trace)
            logs.append(f'{name} seed={seed} PASS')
    socrtl=rtl+sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('perips','sys_bus','top')],[])
    inputs+=socrtl
    run([iv,'-g2012','-s','soc_tb','-o',out/'soc.vvp',*socrtl,ROOT/'simulation/models/pango_ram_models.v',ROOT/'simulation/tb/soc_tb.v'],'soc_compile.log')
    image=ROOT/'simulation/results/prediction.hex';trace=out/'prediction_soc.trace'
    text=run([vvp,out/'soc.vvp',f'+image={image}',f'+trace={trace}',f'+uart={out}/unused_uart.txt'],'prediction_soc.log');assert 'PASS cycles=' in text
    data=(ROOT/'simulation/results/prediction.bin').read_bytes();data+=bytes(65536-len(data));differential(data,trace);logs.append('prediction_soc PASS')
    x=dict(status='PASS',scope='Pilot: 10 variable-latency core runs, prediction/FENCE.I SoC, optional two-way unit model; not full ISA suite',variant=a.variant,tests=logs,
        input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs})
    (out/'result.json').write_text(json.dumps(x,indent=2)+'\n');print('\n'.join(logs))
if __name__=='__main__':main()
