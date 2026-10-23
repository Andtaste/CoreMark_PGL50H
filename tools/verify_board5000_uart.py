"""Validate a saved real-board UART transcript; never infer success from a timeout."""
from pathlib import Path
import argparse,json,hashlib
def verify(path,cpu_hz=83000000):
 text=path.read_text(encoding='utf-8-sig',errors='replace')
 metrics={s.split(':',1)[0].strip():s.split(':',1)[1].strip() for s in text.splitlines() if ':' in s}
 for k,v in {'Configured CPU Hz':str(cpu_hz),'Iterations':'5000','CRC validation':'PASS','Stats ABI signature':'0x4e430004','Stats overflow mask':'0x0000','seedcrc':'0xe9f5','[0]crclist':'0xe714','[0]crcmatrix':'0x1fd7','[0]crcstate':'0x8e3a'}.items():assert metrics.get(k)==v,(k,metrics.get(k),v)
 assert 'Correct operation validated.' in text and 'ERROR!' not in text and 'Errors detected' not in text
 ticks=int(metrics['Total ticks']);seconds=ticks/cpu_hz;assert ticks>=10*cpu_hz,'Runtime below10s'
 assert abs(float(metrics['Total time (secs)'])-seconds)<.0000011
 assert abs(float(metrics['CoreMark/MHz'])-5000*1000000/ticks)<.0000011
 assert abs(float(metrics['Iterations/Sec'])-5000*cpu_hz/ticks)<.0000011
 cycles=int(metrics['Stats window cycles']);retired=int(metrics['Retired instructions']);secondary=int(metrics['Secondary retired'])
 assert 0<retired<=2*cycles and 0<=secondary<=min(cycles,retired)
 assert abs(float(metrics['IPC'])-retired/cycles)<.0011
 assert abs(float(metrics['CPI'])-cycles/retired)<.0011
 assert abs(float(metrics['Secondary slot use'].rstrip('%'))-100*secondary/cycles)<.0011
 return dict(status='PASS',scope='UART transcript checks only; configured clock checked against expected metadata, not independently measured here',iterations=5000,configured_cpu_hz=cpu_hz,benchmark_ticks=ticks,seconds=seconds,coremark_per_mhz=5000*1000000/ticks,iterations_per_second=5000*cpu_hz/ticks,ipc=retired/cycles,secondary_slot_use_percent=100*secondary/cycles,crc_final=metrics['[0]crcfinal'],uart_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
def main():
 p=argparse.ArgumentParser();p.add_argument('uart',type=Path);p.add_argument('--cpu-hz',type=int,default=83000000);a=p.parse_args();r=verify(a.uart,a.cpu_hz);a.uart.with_suffix('.result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
