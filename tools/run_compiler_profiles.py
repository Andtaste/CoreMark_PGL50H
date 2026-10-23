"""Isolated compiler comparison on immutable accepted RTL; never install firmware."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'simulation/results/compiler_profiles_20261023'
PROFILES={'baseline':[], 'o3':['-O3'], 'no_unroll':['-fno-unroll-loops'],
          'schedule':['-fschedule-insns','-fschedule-insns2']}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def linux(p):return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def run(cmd,log,timeout=600):
 with log.open('wb') as f:p=subprocess.run(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 assert p.returncode==0,(log,p.returncode)
 return log.read_text(errors='replace')
def build(profile,count,validation=False):
 # Reuse the production build recipe, adding only documented optimization flags.
 # Stable __DATE__/__TIME__ keeps rebuilds comparable; benchmark source untouched.
 os.environ['SOURCE_DATE_EPOCH']='1792684800'
 script=ROOT/'tools/build_coremark.py';code=script.read_text()
 sys.argv=[str(script),'--iterations',str(count),'--cpu-hz','82000000','--tag','compiler_'+profile,'--profile',profile,'--source-date-epoch','1792684800']+(['--validation'] if validation else [])
 ns={'__file__':str(script),'__name__':'isolated_compiler_build'};exec(compile(code,str(script),'exec'),ns);ns['main']()
 return ROOT/f'sw/build/coremark_{"validation" if validation else "performance"}_{count}_compiler_{profile}/coremark.hex'
def main():
 OUT.mkdir(exist_ok=True)
 manifest=ROOT/'docs/active_optimization_baseline.json';baseline=json.loads(manifest.read_text());src=ROOT/baseline['project_directory']
 for n,h in baseline['input_sha256'].items():assert sha(src/n)==h,n
 ref=ROOT/('simulation/results/load_bp_dual_boundary_auto_'+baseline['source_trial'])
 tb=OUT/'soc_tb.v';s=(ref/'performance/soc_tb.v').read_text()
 assert s.count(' nc_soc dut(')==1 and s.count('localparam UART_DIV=8;')==1
 tb.write_text(s.replace(' nc_soc dut(',' nc_soc #(.CLOCK_HZ(82000000)) dut(').replace('localparam UART_DIV=8;','localparam UART_DIV=9;'))
 uart=OUT/'nc_uart_sim.v';uart.write_text((src/'source/perips/nc_uart.v').read_text().replace('BAUD=115200','BAUD=9375000'))
 actual=[p for folder in ('core','perips','sys_bus','top') for p in sorted((src/'source'/folder).glob('*.v'))]
 actual=[uart if p.name=='nc_uart.v' else p for p in actual]+[ref/'pango_ram_wide_models.v',tb]
 prefix=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--']
 run([*prefix,'verilator','--binary','--timing','-j','4','-Wno-fatal','-DCOREMARK_SIM','--top-module','soc_tb','--Mdir',linux(OUT/'obj'),*[linux(p) for p in actual]],OUT/'compile.log')
 rows=[]
 def evaluate(profile,count=10,validation=False):
  image=build(profile,count,validation);label=profile+('_validation' if validation else '_'+str(count))
  text=run([*prefix,linux(OUT/'obj/Vsoc_tb'),'+image='+linux(image),'+trace='+linux(OUT/(label+'.trace')),'+uart='+linux(OUT/(label+'.uart')),'+notrace=1','+limit=33000000'],OUT/(label+'.log'))
  uart_text=(OUT/(label+'.uart')).read_text()
  assert 'COUNTER_CHECK_PASS' in text and 'PASS cycles=' in text and 'CRC validation   : PASS' in uart_text,label
  metrics={s.split(':',1)[0].strip():s.split(':',1)[1].strip() for s in uart_text.splitlines() if ':' in s}
  for k in ('Configured CPU Hz','Stats overflow mask'):assert metrics[k]=={'Configured CPU Hz':'82000000','Stats overflow mask':'0x0000'}[k]
  prior=json.loads((ref/('validation' if validation else 'performance')/'result.json').read_text())['metrics']
  for k in ('seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal'):assert metrics[k]==prior[k],(label,k)
  cycles=int(metrics['Benchmark cycles64']);retired=int(metrics['Retired instructions'])
  row=dict(profile=profile,count=count,validation=validation,status='PASS',cycles=cycles,cm_per_mhz=count*1e6/cycles,ipc=retired/int(metrics['Stats window cycles']),metrics=metrics,image=str(image.relative_to(ROOT)),image_sha256=sha(image),build=json.loads(image.with_name('build.json').read_text()))
  (OUT/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');print('COMPILER_RESULT',label,cycles,row['cm_per_mhz'],flush=True)
  return row
 for profile in PROFILES:rows.append(evaluate(profile))
 best=min(rows,key=lambda r:r['cycles']);validation=evaluate(best['profile'],1,True)
 # Repeat the winning fixed-image simulation; no recompilation or seed change.
 repeat=evaluate(best['profile'])
 assert repeat['image_sha256']==best['image_sha256'] and repeat['cycles']==best['cycles']
 for n,h in baseline['input_sha256'].items():assert sha(src/n)==h,n
 result=dict(status='PASS',scope='Same accepted RTL, actual82MHz metadata; independent retired counters and CRC. Short diagnostic simulations only. Firmware not installed; physical timing of changed ROM contents not yet verified.',baseline_manifest_sha256=sha(manifest),compiled_sha256={str(p.relative_to(ROOT)):sha(p) for p in actual},profiles=rows,best=best['profile'],gain_pct=100*(rows[0]['cycles']/best['cycles']-1),validation=validation['status'],repeat='PASS')
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print('COMPILER_COMPLETE',result['best'],result['gain_pct'],flush=True)
if __name__=='__main__':main()
