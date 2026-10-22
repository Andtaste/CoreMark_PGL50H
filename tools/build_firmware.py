from pathlib import Path
import argparse,subprocess,shutil
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--gcc');a=p.parse_args()
    gcc=a.gcc or shutil.which('riscv-none-elf-gcc')
    if not gcc:gcc=next(Path('D:/Program Files/riscv').glob('**/riscv-none-elf-gcc.exe'))
    out=ROOT/'sw/build';out.mkdir(parents=True,exist_ok=True)
    subprocess.run([str(gcc),'-O2','-march=rv32im_zicsr','-mabi=ilp32','-msmall-data-limit=0','-mno-relax',
      '-nostdlib','-ffreestanding','-fno-builtin','-Wl,--build-id=none','-T',str(ROOT/'sw/link.lds'),
      str(ROOT/'sw/start.S'),str(ROOT/'sw/demo/main.c'),'-o',str(out/'demo.elf')],check=True)
    objcopy=Path(gcc).with_name(Path(gcc).name.replace('gcc','objcopy'))
    subprocess.run([str(objcopy),'-O','binary',str(out/'demo.elf'),str(out/'demo.bin')],check=True)
    data=(out/'demo.bin').read_bytes();assert 0<len(data)<=65536;data+=bytes(65536-len(data))
    (out/'boot.hex').write_text(''.join(f'{int.from_bytes(data[i:i+4],"little"):08x}\n' for i in range(0,65536,4)))
    shutil.copyfile(out/'boot.hex',out/'demo.hex')
    print('FIRMWARE_OK',out/'boot.hex')
if __name__=='__main__':main()
