"""Run rebuilt frequency-correct validation firmware in the checked clock model."""
from pathlib import Path
import argparse,json,hashlib,subprocess
from clock_trial_args import parse
ROOT=Path(__file__).resolve().parents[1]
def linux(p):p=p.resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def main():
 a=parse()
 out=ROOT/a.checks;image=ROOT/f'sw/build/coremark_validation_1_continuous{a.label}/coremark.hex';exe=out/'obj/Vsoc_tb'
 with (out/'metadata_validation.log').open('wb') as f:
  subprocess.run(['wsl.exe','-d','Ubuntu','--',linux(exe),'+image='+linux(image),'+uart='+linux(out/'metadata_validation.uart'),'+trace='+linux(out/'unused.trace'),'+notrace=1','+limit=33000000'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
 log=(out/'metadata_validation.log').read_text(errors='replace');text=(out/'metadata_validation.uart').read_text()
 assert 'COUNTER_CHECK_PASS' in log and 'PASS cycles=' in log and 'CRC validation   : PASS' in text
 metrics={s.split(':',1)[0].strip():s.split(':',1)[1].strip() for s in text.splitlines() if ':' in s}
 assert metrics['Configured CPU Hz']==str(a.hz) and metrics['Stats overflow mask']=='0x0000'
 for k,v in zip(('seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate'),('18f2','e3c1','0747','8d84')):assert metrics[k]=='0x'+v
 (out/'metadata_result.json').write_text(json.dumps(dict(status='PASS',metrics=metrics,image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),scope='Short validation with actual clock metadata; full5000 image not executed'),indent=2)+'\n')
 print('PASS',a.mhz,'MHz rebuilt validation metadata and CRC')
if __name__=='__main__':main()
