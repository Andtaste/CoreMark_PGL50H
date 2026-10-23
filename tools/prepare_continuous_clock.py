"""Create an isolated real-clock trial from the currently accepted inputs."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess,sys,xml.etree.ElementTree as ET
from clock_trial_args import parse
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 a=parse()
 m=json.loads((ROOT/'docs/active_optimization_baseline.json').read_text());compiler_args=[]
 if a.active_compiler:
  profile=json.loads((ROOT/'docs/active_compiler_profile.json').read_text())
  assert profile['compatible_rtl_manifest_sha256']==sha(ROOT/'docs/active_optimization_baseline.json')
  m=profile['hardware'];compiler_args=['--profile',profile['profile'],'--source-date-epoch',str(profile['source_date_epoch'])]
 parent=ROOT/m['project_directory']
 dest=ROOT/a.project;assert not dest.exists(),dest
 for n,h in m['input_sha256'].items():assert sha(parent/n)==h,n
 dest.mkdir();shutil.copyfile(ROOT/'docs/active_optimization_baseline.json',dest/'parent_baseline.json')
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(parent/folder,dest/folder)
 for p in (dest/'ipcore').rglob('*'):
  if p.is_file() and p.suffix in ('.v','.idf','.vhdl'):p.write_bytes(p.read_bytes().replace(parent.as_posix().encode(),dest.as_posix().encode()))
 if a.active_compiler:shutil.copyfile(ROOT/'docs/active_compiler_profile.json',dest/'parent_compiler_profile.json')
 s=(parent/'new_core.pds').read_text();s=re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',s);(dest/'new_core.pds').write_text(s)
 top=dest/'source/source/top.v';s=top.read_text();old=f"CLOCK_HZ({m['configured_cpu_hz']})";assert s.count(old)==1;top.write_text(s.replace(old,f'CLOCK_HZ({a.hz})'))
 pll=dest/'ipcore/pll/pll.idf';tree=ET.parse(pll)
 values={'STATIC_RATIOI':str(a.ratio_i),'STATIC_RATIOF':str(a.ratio_f),'STATIC_RATIO0':'10','STATIC_DUTY0':'10','STATIC_DUTYF':str(a.ratio_f),'CLKOUT0_REQ_FREQ':f'{float(a.frequency):.4f}'}
 for item in tree.findall('./param_list/param'):
  name=item.findtext('name')
  for k,v in values.items():
   if name in (k+'_basicPage',k+'_advancedPage'):item.find('value').text=v
 tree.write(pll,encoding='utf-8',xml_declaration=True)
 # Only required clock metadata changes; optimization flags remain untouched.
 subprocess.run([sys.executable,str(ROOT/'tools/build_coremark.py'),'--iterations','5000','--cpu-hz',str(a.hz),'--tag',f'continuous{a.label}',*compiler_args],cwd=ROOT,check=True)
 image=ROOT/f'sw/build/coremark_performance_5000_continuous{a.label}/coremark.hex'
 shutil.copyfile(image,dest/'memory/boot.hex')
 words=[int(x,16) for x in image.read_text().split()];assert len(words)==16384
 lines=[]
 for i in range(0,len(words),2):
  data=words[i].to_bytes(4,'little')+words[i+1].to_bytes(4,'little');encoded=bytes(data[j] for j in (0,4,1,5,2,6,3,7));assert bytes(encoded[j] for j in (0,2,4,6,1,3,5,7))==data;lines.append(encoded[::-1].hex())
 image64=dest/'memory/boot_interleaved.hex';image64.write_text('\n'.join(lines)+'\n')
 ram=dest/'ipcore/ram1_tdp/ram1_tdp.idf';tree=ET.parse(ram)
 for item in tree.findall('.//param'):
  if item.findtext('name')=='INIT_FILE':item.find('value').text=image64.as_posix()
 tree.write(ram,encoding='utf-8',xml_declaration=True)
 for ip in (pll,ram):
  with (ip.parent/'continuous_generate.log').open('wb') as stream:
   subprocess.run(['E:/pango/PDS_2022.2-SP1-Lite/bin/ip_generate.exe','-i',str(ip),'-disable-syn'],cwd=ip.parent,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=180)
 text=(pll.parent/'pll.v').read_text()
 for k,v in (('STATIC_RATIOI',a.ratio_i),('STATIC_RATIOF',a.ratio_f),('STATIC_RATIO0',10)):assert re.search(r'\b'+k+r'\s*=\s*'+str(v)+r';',text)
 for p in (dest/'source/core').glob('*.v'):assert sha(p)==sha(parent/'source/core'/p.name)
 inputs={str(p.relative_to(dest)):sha(p) for folder in ('source','ipcore','constraints','memory') for p in (dest/folder).rglob('*') if p.is_file()}
 (dest/'prepared.json').write_text(json.dumps(dict(status='PREPARED',cpu_hz=a.hz,uart_divisor=(a.hz+57600)//115200,parent=str(parent.relative_to(ROOT)),input_sha256=inputs,software_build=str(image.with_name('build.json').relative_to(ROOT))),indent=2)+'\n')
 print('PREPARED',dest)
if __name__=='__main__':main()
