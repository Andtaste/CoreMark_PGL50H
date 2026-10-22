"""Execute the installed 5000-iteration firmware; no shortened loop or skipped CPU cycles."""
from pathlib import Path
import argparse,hashlib,json,subprocess,re,time,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def linux(p):p=p.resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--full-run',action='store_true',help='Explicitly execute all5000 iterations; not run by default');args=parser.parse_args()
 project=ROOT/'hardware/pds';out=ROOT/'simulation/results/board5000';out.mkdir(exist_ok=True)
 prefix=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--']
 actual=[p for d in ('core','perips','sys_bus','top') for p in sorted((project/'source'/d).glob('*.v'))]
 model=ROOT/'simulation/models/pango_ram_wide_models.v';shutil.copyfile(model,out/'pango_ram_wide_models.v');model=out/'pango_ram_wide_models.v'
 uart=out/'nc_uart_sim.v';s=(project/'source/perips/nc_uart.v').read_text();assert s.count('BAUD=115200')==1;uart.write_text(s.replace('BAUD=115200','BAUD=10250000'))
 tb=ROOT/'simulation/tb/board5000_tb.v';sources=[uart if p.name=='nc_uart.v' else p for p in actual]+[model,tb]
 hashes={str(p.relative_to(ROOT)):sha(p) for p in sources}
 with (out/'compile.log').open('wb') as f:subprocess.run([*prefix,'verilator','--binary','--timing','-j','4','-Wno-fatal','--top-module','board5000_tb','--Mdir',linux(out/'obj'),*[linux(p) for p in sources]],stdout=f,stderr=subprocess.STDOUT,check=True)
 results={}
 runs=[('validation','coremark_validation_1_board82')]
 if args.full_run:runs.append(('performance','coremark_performance_5000'))
 for label,name in runs:
  image=ROOT/'sw/build'/name/'coremark.hex';start=time.monotonic();hashes[str(image.relative_to(ROOT))]=sha(image)
  with (out/(label+'.log')).open('wb') as f:subprocess.run([*prefix,linux(out/'obj/Vboard5000_tb'),'+image='+linux(image),'+uart='+linux(out/(label+'.uart')),'+limit=2000000000'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=7200)
  text=(out/(label+'.uart')).read_text();log=(out/(label+'.log')).read_text(errors='replace')
  assert 'CRC validation   : PASS' in text and 'COUNTER_CHECK_PASS' in log and 'PASS board firmware' in log,(label,text,log[-2000:])
  metrics={s.split(':',1)[0].strip():s.split(':',1)[1].strip() for s in text.splitlines() if ':' in s}
  assert metrics['Configured CPU Hz']=='82000000' and metrics['Stats overflow mask']=='0x0000'
  for key,value in zip(('seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate'),('18f2','e3c1','0747','8d84') if label=='validation' else ('e9f5','e714','1fd7','8e3a')):assert metrics[key]=='0x'+value,(label,key)
  cycles=int(metrics['Stats window cycles']);retired=int(metrics['Retired instructions']);ipc=retired/cycles
  assert abs(float(metrics['IPC'])-ipc)<.0011 and 0<retired<=2*cycles
  if label=='performance':
   assert metrics['Iterations']=='5000' and float(metrics['Total time (secs)'])>=10
   assert 'Correct operation validated.' in text and 'ERROR!' not in text and 'Errors detected' not in text
  results[label]=dict(status='PASS',wall_seconds=time.monotonic()-start,metrics=metrics,ipc=ipc,image_sha256=sha(image),simulation_only_uart_divisor=8)
  (out/(label+'_result.json')).write_text(json.dumps(results[label],indent=2)+'\n');print('PASS',label,'cycles',cycles,'IPC',ipc,flush=True)
 for n,h in hashes.items():assert sha(ROOT/n)==h,n
 result=dict(status='PASS',scope='RTL simulation; not a board measurement',full5000_simulation_completed=args.full_run,validation=results['validation'],performance=results.get('performance'),input_sha256=hashes)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');shutil.copyfile(out/'result.json',ROOT/'docs/board5000_20261022/simulation_result.json')
if __name__=='__main__':main()
