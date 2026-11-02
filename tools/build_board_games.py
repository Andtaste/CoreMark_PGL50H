"""Build one CPU/firmware for both games; adapt existing engine sources once.

The generated adapters only relocate private storage/address; algorithms remain
in sw/gomoku and sw/xiangqi, avoiding maintained copies of either engine.
"""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess,sys,xml.etree.ElementTree as ET
N=Path(__file__).resolve().parents[1];P=N/'hardware/board_games';S=N/'sw/board_games';O=N/'sw/build/board_games'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args,log,cwd=None):
 q=subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True);b=q.stdout+q.stderr;Path(log).write_bytes(b)
 if q.returncode or re.search(rb'^E:|FATAL:',b,re.M):raise RuntimeError(b.decode(errors='replace')[-4000:])
 return b.decode(errors='replace')
def adapt():
 O.mkdir(parents=True,exist_ok=True)
 g=(N/'sw/gomoku/engine.c').read_text()
 for line in ['static Entry table[TT_SIZE]; /* 8192 bytes on the target. */','static GMove lists[G_MAX_PLY][G_CANDIDATES];','static uint32_t nodes,hits,cuts,limit;','static int interrupted;','static GStop stop_fn;static void *stop_context;']:
  assert g.count(line)==1,line;g=g.replace(line,'')
 for name in ['table','lists','nodes','hits','cuts','limit','interrupted','stop_fn','stop_context']:
  g=re.sub(r'(?<![.\w])'+name+r'\b','GW.'+name,g)
 context='''
typedef struct {Entry table[TT_SIZE];GMove lists[G_MAX_PLY][G_CANDIDATES];
 uint32_t nodes,hits,cuts,limit;int interrupted;GStop stop_fn;void *stop_context;Gomoku game;} GWork;
extern unsigned char board_workspace[32400];
typedef char workspace_must_fit[(sizeof(GWork)<=32400)?1:-1];
#define GW (*(GWork *)(void *)board_workspace)
Gomoku *g_platform_game(void){return &GW.game;}
'''
 marker='typedef struct {uint64_t key;int32_t score;uint16_t move;uint8_t depth,bound;} Entry;'
 assert marker in g;g=g.replace(marker,marker+context).replace('0x20004000u','0x20008000u')
 (O/'gomoku_engine.c').write_text(g)
 x=(N/'sw/xiangqi/engine.cpp').read_text();decl='static int32_t history[90*90] __attribute__((section(".history"),aligned(64)));'
 assert x.count(decl)==1
 x=x.replace(decl,'extern "C" unsigned char board_workspace[32400];\n#define history (*(int32_t (*)[90*90])(void *)board_workspace)')
 (O/'xiangqi_engine.cpp').write_text(x)
CM_FLAGS=['-O2','-fno-common','-fno-strict-aliasing','-ffunction-sections','-fdata-sections','-fno-builtin','-fno-lto']
def coremark_objects(compiler,base,prefix):
 files=[N/'sw/coremark'/name for name in ['core_main.c','core_list_join.c','core_matrix.c','core_state.c','core_util.c']]+[N/'sw/lib/xprintf.c',S/'coremark_port.c']
 objects=[]
 profile=json.loads((S/'coremark_profile.json').read_text())
 target='-DHOST_BUILD' not in base
 common=profile['flags'] if target else CM_FLAGS
 modules=profile['modules'] if target else {}
 reported=' '.join(base+common)+''.join(' ['+name+': '+' '.join(opts)+']' for name,opts in modules.items())
 for f in files:
  out=O/(prefix+f.stem+'.o');opts=['-Dmain=board_coremark_main'] if f.name=='core_main.c' else []
  chosen=common+modules.get(f.name,[])
  run([compiler,*base,*chosen,'-std=c99','-I',N/'sw/coremark','-DFLAGS_STR="'+reported+'"',*opts,'-c',f,'-o',out],O/(prefix+f.stem+'.log'));objects.append(out)
 return objects

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--ip',action='store_true');ap.add_argument('--pds',action='store_true');ap.add_argument('--host-only',action='store_true');ap.add_argument('--software-only',action='store_true');a=ap.parse_args();assert not (a.ip or a.pds), 'Use tools/reproduce.py ip and the supplied PDS project';adapt()
 assert not (a.software_only and (a.ip or a.pds)),'software-only cannot run IP/PDS'
 from game_clock import static_clocks
 hz=round(static_clocks(P/'ipcore/pll/pll.v')['out0_hz']);assert 70000000<=hz<=103000000
 assert '.CLOCK_HZ('+str(hz)+')' in (P/'source/top/top.v').read_text()
 hostflags=['-O2','-fno-strict-aliasing','-DHOST_BUILD','-DCPU_HZ='+str(hz)]
 run(['gcc',*hostflags,'-std=c99','-I',N/'sw/gomoku','-c',O/'gomoku_engine.c','-o',O/'host_gomoku.o'],O/'host_gomoku.log')
 run(['gcc',*hostflags,'-c',S/'workspace.c','-o',O/'host_workspace.o'],O/'host_workspace.log')
 cm_host=coremark_objects('gcc',hostflags,'host_cm_')
 run(['g++',*hostflags,'-std=c++11','-fsigned-char','-I',N/'sw/xiangqi',S/'main.cpp',O/'xiangqi_engine.cpp',O/'host_gomoku.o',O/'host_workspace.o',*cm_host,'-o',O/'board_games_host.exe'],O/'host.log')
 if a.host_only:print('HOST_BUILD_PASS',flush=True);return
 gcc=Path(shutil.which('riscv-none-elf-gcc') or next(Path('D:/Program Files/riscv').glob('**/riscv-none-elf-gcc.exe')));gxx=gcc.with_name(gcc.name.replace('gcc','g++'))
 flags=['-march=rv32im_zicsr','-mabi=ilp32','-msmall-data-limit=0','-mno-relax','-nostdlib','-ffreestanding','-fno-builtin','-ffunction-sections','-fdata-sections','-fno-strict-aliasing','-DCPU_HZ='+str(hz)]
 run([gcc,*flags,'-O2','-std=c99','-DGOMOKU_HW','-I',N/'sw/gomoku','-c',O/'gomoku_engine.c','-o',O/'gomoku_engine.o'],O/'gomoku_build.log')
 run([gcc,*flags,'-O2','-c',S/'workspace.c','-o',O/'workspace.o'],O/'workspace_build.log')
 cm_target=coremark_objects(gcc,flags,'cm_')
 command=[gxx,*flags,'-flto','-O3','-std=c++11','-fsigned-char','-fno-exceptions','-fno-rtti','-fno-threadsafe-statics','-DXQ_ATTACK_ACCEL=1','-DXQ_RAY_ACCEL=1','-I',N/'sw/xiangqi',
  '-T',S/'link.lds','-Wl,--gc-sections','-Wl,--build-id=none','-Wl,-Map='+str(O/'board_games.map'),S/'start.S',S/'main.cpp',O/'xiangqi_engine.cpp',S/'runtime.cpp',O/'gomoku_engine.o',O/'workspace.o',*cm_target,'-lgcc','-o',O/'board_games.elf']
 run(command,O/'firmware_build.log')
 run([gcc.with_name(gcc.name.replace('gcc','objcopy')),'-O','binary',O/'board_games.elf',O/'board_games.bin'],O/'objcopy.log')
 size=run([gcc.with_name(gcc.name.replace('gcc','size')),O/'board_games.elf'],O/'size.log');print(size,flush=True)
 symbols=run([gcc.with_name(gcc.name.replace('gcc','nm')),'-n','-C',O/'board_games.elf'],O/'symbols.log')
 assert re.search(r'^10000000 [bBdD] pos\r?$',symbols,re.M),'Fixed snooped board moved'
 data=(O/'board_games.bin').read_bytes();assert 0<len(data)<=98304,'Combined code does not fit96KiB';data=data.ljust(98304,b'\0')
 for width,name in [(4,'boot.hex'),(8,'boot64.hex')]:
  (P/'memory'/name).write_text(''.join(data[i:i+width][::-1].hex()+'\n' for i in range(0,len(data),width)))
 for name,block in [('boot_base64.hex',data[:65536]),('boot_tail64.hex',data[65536:])]:
  (P/'memory'/name).write_text(''.join(block[i:i+8][::-1].hex()+'\n' for i in range(0,len(block),8)))
 (O/'build.json').write_text(json.dumps(dict(cpu_hz=hz,command=list(map(str,command)),size=size,binary_sha256=sha(O/'board_games.bin'),input_sha256={f.relative_to(N).as_posix():sha(f) for folder in [S,N/'sw/gomoku',N/'sw/xiangqi',N/'sw/coremark',N/'sw/include',N/'sw/lib'] for f in folder.rglob('*') if f.is_file()},workspace_bytes=32400,workspace_policy='Mutually exclusive Xiangqi history/Gomoku state;shared48KiB-minimum search stack'),indent=2))
 print('BOARD_GAMES_SOFTWARE_BUILD_PASS',flush=True)
if __name__=='__main__':main()
