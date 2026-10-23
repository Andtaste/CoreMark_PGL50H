"""Exercise production reporting on current RTL with captured large counters."""
from pathlib import Path
import json,subprocess,sys,os
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'simulation/results/report_large_20261023'
def linux(p):return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def run(cmd,log):
 with log.open('wb') as f:r=subprocess.run(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=600)
 assert r.returncode==0,log
 return log.read_text(errors='replace')
def main():
 OUT.mkdir(exist_ok=True)
 label=sys.argv[1] if len(sys.argv)>1 else 'before'
 source=(ROOT/'sw/coremark/core_portme.c').read_text().replace('"../include/', '"'+(ROOT/'sw/include').as_posix()+'/')
 source+='''
void inject_report(void) {
 stats_present=1;stats_version=4;t0=0;t1=1149771717ULL;
 stats[0]=1149771754U;stats[7]=0;retired_instructions=1270809719U;
 secondary_retired=371669116U;loads=259142833U;stores=66925563U;
 operand_wait=146058015U;id_blocked=169838456U;
 stats[2]=53861796U;stats[3]=20125170U;stats[5]=26930898U;stats[6]=253526584U;
}
'''
 port=OUT/(label+'_port.c');port.write_text(source)
 fixture=OUT/'main.c';fixture.write_text('#include "coremark.h"\nvoid inject_report(void);\nint main(void){core_portable p;portable_init(&p,0,0);inject_report();portable_print_timing(1149771717ULL,5000);portable_fini(&p);return 1;}\n')
 original=json.loads((ROOT/'sw/build/coremark_performance_5000_continuous83_inline80_sweep/build.json').read_text())['command'];cmd=[]
 for x in original:
  if x.endswith('core_main.c'):x=str(fixture)
  elif x.endswith('core_portme.c'):x=str(port)
  elif x.startswith('-Wl,-Map='):x='-Wl,-Map='+str(OUT/(label+'.map'))
  elif x.endswith('coremark.elf'):x=str(OUT/(label+'.elf'))
  cmd.append(x)
 cmd+=['-I',str(ROOT/'sw/coremark')];os.environ['SOURCE_DATE_EPOCH']='1792684800';run(cmd,OUT/(label+'_build.log'))
 gcc=Path(cmd[0]);run([gcc.with_name(gcc.name.replace('gcc','objcopy')),'-O','binary',OUT/(label+'.elf'),OUT/(label+'.bin')],OUT/(label+'_objcopy.log'))
 with (OUT/(label+'.dump')).open('w') as f:subprocess.run([str(gcc.with_name(gcc.name.replace('gcc','objdump'))),'-d',str(OUT/(label+'.elf'))],stdout=f,check=True)
 b=(OUT/(label+'.bin')).read_bytes();assert len(b)<=65536;b+=bytes(65536-len(b));image=OUT/(label+'.hex');image.write_text(''.join(f'{int.from_bytes(b[i:i+4],"little"):08x}\n' for i in range(0,65536,4)))
 prefix=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--']
 if not (OUT/'obj/Vsoc_tb').exists():
  tb=OUT/'soc_tb.v';tb.write_bytes((ROOT/'simulation/results/continuous_clock83_inline80_sweep_checks/soc_tb.v').read_bytes())
  uart=OUT/'nc_uart_sim.v';uart.write_text((ROOT/'hardware/pds/source/perips/nc_uart.v').read_text().replace('BAUD=115200','BAUD=9375000'))
  actual=[p for f in ('core','perips','sys_bus','top') for p in (ROOT/'hardware/pds/source'/f).glob('*.v')];actual=[uart if p.name=='nc_uart.v' else p for p in actual]
  run([*prefix,'verilator','--binary','--timing','-j','4','-Wno-fatal','-DCOREMARK_SIM','--top-module','soc_tb','--Mdir',linux(OUT/'obj'),*[linux(p) for p in actual],linux(ROOT/'simulation/models/pango_ram_wide_models.v'),linux(tb)],OUT/'compile.log')
 text=run([*prefix,linux(OUT/'obj/Vsoc_tb'),'+image='+linux(image),'+trace='+linux(OUT/(label+'.trace')),'+uart='+linux(OUT/(label+'.uart')),'+notrace=1','+limit=5000000'],OUT/(label+'.log'));assert 'PASS cycles=' in text
 print((OUT/(label+'.uart')).read_text())
if __name__=='__main__':main()
