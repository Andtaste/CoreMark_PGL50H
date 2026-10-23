"""Validate a longer compiler comparison and build isolated actual82MHz O3 ROM."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess,xml.etree.ElementTree as ET
import run_compiler_profiles as cp
ROOT=cp.ROOT
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--profile',choices=['o3','o3_inline80'],default='o3');args=ap.parse_args();selected=args.profile
 cp.PROFILES['o3_inline80']=['-O3','--param=max-inline-insns-auto=80']
 out=cp.OUT;prefix=['wsl.exe','-d','Ubuntu','--cd',cp.linux(ROOT),'--'];rows=[]
 for profile in (() if selected=='o3_inline80' else ('baseline','o3')):
  image=cp.build(profile,100);label=profile+'_100'
  text=cp.run([*prefix,cp.linux(out/'obj/Vsoc_tb'),'+image='+cp.linux(image),'+trace='+cp.linux(out/(label+'.trace')),'+uart='+cp.linux(out/(label+'.uart')),'+notrace=1','+limit=100000000'],out/(label+'.log'))
  printed=(out/(label+'.uart')).read_text();assert 'CRC validation   : PASS' in printed and 'COUNTER_CHECK_PASS' in text and 'PASS cycles=' in text
  metrics={s.split(':',1)[0].strip():s.split(':',1)[1].strip() for s in printed.splitlines() if ':' in s}
  ref=json.loads((out/(profile+'_10.json')).read_text())['metrics']
  for k in ('seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate'):assert metrics[k]==ref[k],k
  # The accumulated crcfinal depends on iteration count. Compare it only
  # between baseline and O3 at the same count; algorithm CRCs remain fixed.
  if rows:assert metrics['[0]crcfinal']==rows[0]['metrics']['[0]crcfinal']
  row={'profile':profile,'count':100,'status':'PASS','metrics':metrics,'cycles':int(metrics['Benchmark cycles64']),'image_sha256':cp.sha(image)};rows.append(row)
  print('COMPILER_100',profile,row['cycles'],flush=True)
 if selected=='o3_inline80':
  rows=[json.loads((out/'longer_comparison.json').read_text())['runs'][0],json.loads((out/'o3_inline80_100.json').read_text())]
  assert rows[1]['status']=='PASS' and rows[1]['metrics']['[0]crcfinal']==rows[0]['metrics']['[0]crcfinal']
  assert cp.sha(ROOT/rows[1]['image'])==rows[1]['image_sha256']
 else:(out/'longer_comparison.json').write_text(json.dumps({'status':'PASS','runs':rows,'gain_pct':100*(rows[0]['cycles']/rows[1]['cycles']-1)},indent=2)+'\n')
 assert rows[1]['cycles']<rows[0]['cycles']
 image=cp.build(selected,5000)
 m=json.loads((ROOT/'docs/active_optimization_baseline.json').read_text());src=ROOT/m['project_directory'];dest=ROOT/f'simulation/results/continuous_clock82_shortmul_{selected}_20261022';assert not dest.exists()
 for n,h in m['input_sha256'].items():assert cp.sha(src/n)==h,n
 dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
 shutil.copyfile(ROOT/'docs/active_optimization_baseline.json',dest/'parent_baseline.json')
 for p in (dest/'ipcore').rglob('*'):
  if p.is_file() and p.suffix in ('.v','.idf','.vhdl'):p.write_bytes(p.read_bytes().replace(src.as_posix().encode(),dest.as_posix().encode()))
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
 with (ram.parent/'compiler_o3_generate.log').open('wb') as f:subprocess.run(['E:/pango/PDS_2022.2-SP1-Lite/bin/ip_generate.exe','-i',str(ram),'-disable-syn'],cwd=ram.parent,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=180)
 s=re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text());(dest/'new_core.pds').write_text(s)
 for p in (dest/'source').rglob('*.v'):assert cp.sha(p)==cp.sha(src/p.relative_to(dest))
 meta=dict(status='PREPARED',cpu_hz=82000000,uart_divisor=712,parent=str(src.relative_to(ROOT)),strategy='software_'+selected,changed_option={},place_seed=3,route_seed=1,software_build=str(image.with_name('build.json').relative_to(ROOT)),scope='Accepted82MHz RTL/PLL/constraints and seeds unchanged. Selected compiler profile firmware and corresponding instruction RAM initialization only. Diagnostic compiler gain measured separately; actual5000 image needs physical verification.',input_sha256={str(p.relative_to(dest)):cp.sha(p) for folder in ('source','ipcore','constraints','memory') for p in (dest/folder).rglob('*') if p.is_file()})
 (dest/'prepared.json').write_text(json.dumps(meta,indent=2)+'\n')
 print('PREPARED',dest,flush=True)
 with (dest/'native_build.log').open('wb') as f:subprocess.run(['E:/pango/PDS_2022.2-SP1-Lite/bin/pds_shell.exe','-project','new_core.pds','-run','report_timing'],cwd=dest,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=3600)
if __name__=='__main__':main()
