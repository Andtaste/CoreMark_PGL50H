"""Clone accepted source; specialize secondary execution and generate genuine PLL80."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',default='dual_boundary_side');a=ap.parse_args()
 assert a.variant in ('dual_boundary_side','dual_boundary_clock')
 accepted=ROOT/'docs/accepted_dual_baseline.json';d=json.loads(accepted.read_text(encoding='utf-8'));assert d['variant']=='dual_boundary_launch'
 src=ROOT/d['source_directory'];out=src.with_name('load_bp_'+a.variant);assert not out.exists();out.mkdir()
 g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 if a.variant.endswith('_side'):
  p=out/'nc_core.v';s=p.read_text();old='.packet(ex_side[203:0]),.control(ex_side[222:204]),';assert s.count(old)==1
  s=s.replace(old,'.packet(ex_side[203:0]),.control({2\'b0,ex_side[220:204]}),')
  s=s.replace(' nc_execute #(.ENABLE_DIV(0)) execute1',' // Side admission permits conditional branches, ALU and MUL only.\n // Tie JAL/JALR control off at this boundary, removing unused AGU/target\n // comparisons from the secondary prediction path; no added cycle.\n nc_execute #(.ENABLE_DIV(0)) execute1');p.write_text(s)
 pll=out/'ipcore/pll';shutil.copytree(ROOT/'hardware/pds/ipcore/pll',pll)
 p=pll/'pll.idf';tree=ET.parse(p)
 # 50 / 5 * 64 / 8 = 80MHz, VCO=640MHz. Both GUI pages agree.
 values={'STATIC_RATIOI':'5','STATIC_RATIOF':'64','STATIC_RATIO0':'8','STATIC_DUTY0':'8','STATIC_DUTYF':'64','CLKOUT0_REQ_FREQ':'80.0000'}
 for item in tree.findall('./param_list/param'):
  name=item.findtext('name')
  for key,value in values.items():
   if name in (key+'_basicPage',key+'_advancedPage'):item.find('value').text=value
 tree.write(p,encoding='UTF-8',xml_declaration=True)
 with (pll/'timing80_generate.log').open('wb') as log:
  x=subprocess.run([r'E:\pango\PDS_2022.2-SP1-Lite\bin\ip_generate.exe','-i',str(p),'-disable-syn'],cwd=pll,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 assert x.returncode==0
 text=(pll/'pll.v').read_text();assert 'STATIC_RATIOI    = 5;' in text and 'STATIC_RATIOF    = 64;' in text
 for key in g['override_sha256']:g['override_sha256'][key]=sha(out/Path(key).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),accepted_dual_sha256=sha(accepted),scope=a.variant+'; PLL80 isolated implementation; secondary jump specialization only in side variant; unchanged cycle architecture; research not adopted',requested_clock_mhz=80)
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED '+a.variant)
if __name__=='__main__':main()
