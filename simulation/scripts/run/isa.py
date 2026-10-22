from pathlib import Path
import json,hashlib,shutil,argparse
from regression import ROOT,OUT,find,run
def main():
    p=argparse.ArgumentParser();p.add_argument('--import-from',type=Path);p.add_argument('--iverilog');p.add_argument('--vvp');a=p.parse_args()
    ref=ROOT/'references/isa';ref.mkdir(parents=True,exist_ok=True)
    if a.import_from:
        manifest=[]
        for src in sorted((a.import_from/'generated').glob('*.bin')):
            target=ref/'generated'/src.name;target.parent.mkdir(exist_ok=True);shutil.copy2(src,target)
            manifest.append({'file':src.name,'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest()})
        for dirname in ('rv32ui','rv32um'):shutil.copytree(a.import_from/dirname,ref/dirname,dirs_exist_ok=True)
        for name in ('README.md','riscv_test.h','test_macros.h','link.ld','Makefile'):shutil.copy2(a.import_from/name,ref/name)
        (ref/'PROVENANCE.json').write_text(json.dumps(manifest,indent=2))
    iv=a.iverilog or find('iverilog',[ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe'])
    vvp=a.vvp or find('vvp',[ROOT.parent/'tmp/iverilog-portable/bin/vvp.exe'])
    rtl=[p for directory in ('core','perips','sys_bus','top') for p in (ROOT/'hardware/pds/source'/directory).glob('*.v')]
    run([iv,'-g2012','-s','soc_tb','-o',OUT/'isa.vvp',*rtl,ROOT/'simulation/models/pango_ram_models.v',ROOT/'simulation/tb/soc_tb.v'],OUT/'isa_compile.log')
    results=[];tests=sorted((ref/'generated').glob('*.bin'));assert len(tests)==47,len(tests)
    for src in tests:
        data=src.read_bytes();assert len(data)<=65536;data+=bytes(65536-len(data))
        image=OUT/'isa.hex';image.write_text(''.join(f'{int.from_bytes(data[i:i+4],"little"):08x}\n' for i in range(0,65536,4)))
        output=run([vvp,OUT/'isa.vvp',f'+image={image}',f'+trace={OUT / (src.stem+".trace")}', '+legacy=1','+limit=100000'],OUT/(src.stem+'.log'))
        assert 'PASS cycles=' in output,(src.name,output)
        results.append({'test':src.stem,'status':'PASS','summary':output.strip()});print(src.stem,'PASS',flush=True)
    (OUT/'isa.json').write_text(json.dumps({'scope':'47 inherited RV32I/M fixtures, not a complete architecture compliance suite','results':results},indent=2))
if __name__=='__main__':main()
