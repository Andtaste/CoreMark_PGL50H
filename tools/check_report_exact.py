"""Replay original machine-code reporting with captured values; do not recompile it."""
from pathlib import Path
import json,subprocess
from check_report_large import ROOT,OUT,linux,run
def main():
 folder=ROOT/'sw/build/coremark_performance_5000_continuous83_inline80_sweep';gcc=Path(json.loads((folder/'build.json').read_text())['command'][0])
 symbols=subprocess.check_output([str(gcc.with_name(gcc.name.replace('gcc','nm'))),'-n',str(folder/'coremark.elf')],text=True)
 sym={parts[2]:int(parts[0],16) for line in symbols.splitlines() if len(parts:=line.split())==3}
 asm=['.section .text','.globl _start','_start:','li a0,0','li a1,0','li a2,0',f'li t0,{sym["portable_init"]}','jalr ra,0(t0)']
 values={'stats_present':1,'stats_version':4,'t0':0,'t1':1149771717,'retired_instructions':1270809719,'secondary_retired':371669116,'loads':259142833,'stores':66925563,'operand_wait':146058015,'id_blocked':169838456}
 for n,v in values.items():asm += [f'li t0,{sym[n]}',f'li t1,{v}','sw t1,0(t0)']
 for i,v in enumerate([1149771754,0,53861796,20125170,0,26930898,253526584,0]):asm += [f'li t0,{sym["stats"]+4*i}',f'li t1,{v}','sw t1,0(t0)']
 asm+=['li a0,1149771717','li a1,0','li a2,5000',f'li t0,{sym["portable_print_timing"]}','jalr ra,0(t0)','li a0,0',f'li t0,{sym["portable_fini"]}','jalr ra,0(t0)','li a0,1','li t0,0x74','jr t0']
 source=OUT/'exact_stub.S';source.write_text('\n'.join(asm)+'\n')
 run([gcc,'-march=rv32im_zicsr','-mabi=ilp32','-mno-relax','-nostdlib','-Wl,--no-relax','-Wl,-Ttext=0xf000',source,'-o',OUT/'exact_stub.elf'],OUT/'exact_build.log')
 run([gcc.with_name(gcc.name.replace('gcc','objcopy')),'-O','binary',OUT/'exact_stub.elf',OUT/'exact_stub.bin'],OUT/'exact_copy.log')
 b=bytearray((folder/'coremark.bin').read_bytes());b+=bytes(65536-len(b));stub=(OUT/'exact_stub.bin').read_bytes();assert len(stub)<4096;b[0xf000:0xf000+len(stub)]=stub
 b[0x6c:0x74]=(0xf0b7).to_bytes(4,'little')+(0x000080e7).to_bytes(4,'little')
 image=OUT/'exact.hex';image.write_text(''.join(f'{int.from_bytes(b[i:i+4],"little"):08x}\n' for i in range(0,65536,4)))
 prefix=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--'];run([*prefix,linux(OUT/'obj/Vsoc_tb'),'+image='+linux(image),'+trace='+linux(OUT/'exact.trace'),'+uart='+linux(OUT/'exact.uart'),'+notrace=0','+limit=5000000'],OUT/'exact.log')
 print((OUT/'exact.uart').read_text())
if __name__=='__main__':main()
