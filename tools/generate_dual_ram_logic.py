"""Same issue policy, balanced encoded producer selection and correct A64 init."""
from pathlib import Path
import hashlib,json,shutil,subprocess,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 src=ROOT/'simulation/results/load_bp_dual_ram_wide';dest=src.with_name('load_bp_dual_ram_logic');dest.mkdir(exist_ok=True)
 meta=json.loads((src/'generation.json').read_text())
 for n,h in meta['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h,n;shutil.copyfile(p,dest/p.name)
 p=dest/'nc_core.v';s=p.read_text()
 start=s.index(' function [2:0] newest;');end=s.index(' endfunction',start)+len(' endfunction')
 s=s[:start]+''' // Four-bit encoded identity is retained. Encode interleaved lanes in
 // a balanced tree, rather than encode group then dynamically select lane.
 function [3:0] newest4;
  input[15:0] mask;
  reg[1:0] q0,q1,q2,q3;reg[2:0] lo,hi;
  begin
   q0={|mask[3:2],mask[3] || (!mask[2] && mask[1])};
   q1={|mask[7:6],mask[7] || (!mask[6] && mask[5])};
   q2={|mask[11:10],mask[11] || (!mask[10] && mask[9])};
   q3={|mask[15:14],mask[15] || (!mask[14] && mask[13])};
   lo={|mask[7:4],(|mask[7:4] ? q1 : q0)};
   hi={|mask[15:12],(|mask[15:12] ? q3 : q2)};
   newest4={|mask[15:8],(|mask[15:8] ? hi : lo)};
  end
 endfunction'''+s[end:]
 s=rep(s,'reg[7:0] match_a,match_b,below_tail;', 'reg[7:0] match_a,match_b,below_tail;reg[15:0] producers_a,producers_b,below_tail16;')
 old='''  tag_a[3:1]=|((match_a|match_a1) & below_tail) ? newest((match_a|match_a1) & below_tail) : newest(match_a|match_a1);
  tag_b[3:1]=|((match_b|match_b1) & below_tail) ? newest((match_b|match_b1) & below_tail) : newest(match_b|match_b1);
  tag_a[0]=match_a1[tag_a[3:1]];tag_b[0]=match_b1[tag_b[3:1]];'''
 new='''  for(n=0;n<8;n=n+1) begin
   producers_a[2*n]=match_a[n];producers_a[2*n+1]=match_a1[n];
   producers_b[2*n]=match_b[n];producers_b[2*n+1]=match_b1[n];
   below_tail16[2*n]=below_tail[n];below_tail16[2*n+1]=below_tail[n];
  end
  tag_a=|(producers_a & below_tail16) ? newest4(producers_a & below_tail16) : newest4(producers_a);
  tag_b=|(producers_b & below_tail16) ? newest4(producers_b & below_tail16) : newest4(producers_b);'''
 s=rep(s,old,new)
 s=rep(s,'reg f1_valid;reg[2:0] f1_tag;reg[31:0] f1_data;', 'reg f1_valid;wire[2:0] f1_tag=f_tag;reg[31:0] f1_data;')
 s=rep(s,'begin f1_tag<=ex_tag;f1_data<=', 'begin f1_data<=')
 p.write_text(s)
 p=dest/'nc_fetch.v';p.write_text(rep(p.read_text()," wire[31:0] lookup_pc1=next_pc+32'd4;\n",''))
 p=dest/'nc_local_bus.v';p.write_text(rep(p.read_text()," wire[31:0] ia_lo={ia[31:3],3'b000},ia_hi={ia[31:3],3'b100};",''))
 shutil.copyfile(src/'pango_ram_wide_models.v',dest/'pango_ram_wide_models.v')
 # PDS 2022.2's init script packs contiguous 16-bit primitive chunks.
 # The A64/B32 RTL maps each chunk's two bytes into opposite 32-bit words.
 # Inverse byte interleaving is therefore required in the generator input.
 # Vendor primitive readback (all words, both ports, byte writes) validates
 # this encoding, rather than relying on the behavioral CPU memory model.
 words=[int(x,16) for x in (ROOT/'sw/build/boot.hex').read_text().split()];lines=[]
 for i in range(0,len(words),2):
  data=words[i].to_bytes(4,'little')+words[i+1].to_bytes(4,'little');encoded=bytes(data[j] for j in (0,4,1,5,2,6,3,7))
  decoded=bytes(encoded[j] for j in (0,2,4,6,1,3,5,7));assert decoded==data
  lines.append(encoded[::-1].hex())
 image=dest/'boot_interleaved.hex';image.write_text('\n'.join(lines)+'\n')
 ipfiles=[]
 for name in ('ram1_tdp','ram2_tdp'):
  source=src/f'ipcore/{name}/{name}.idf';folder=dest/'ipcore'/name;folder.mkdir(parents=True,exist_ok=True);path=folder/(name+'.idf');tree=ET.parse(source)
  if name=='ram1_tdp':
   for item in tree.findall('.//param'):
    if item.findtext('name')=='INIT_FILE':item.find('value').text=image.as_posix()
  tree.write(path,encoding='utf-8',xml_declaration=True)
  with (folder/'regenerate.log').open('wb') as f:x=subprocess.run([r'E:\pango\PDS_2022.2-SP1-Lite\bin\ip_generate.exe','-i',str(path),'-disable-syn'],cwd=folder,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  assert x.returncode==0,(name,(folder/'regenerate.log').read_text(errors='replace')[-3000:])
  ipfiles.extend(p for p in folder.rglob('*') if p.is_file() and p.suffix in ('.idf','.v'))
 for n in meta['override_sha256']:meta['override_sha256'][n]=sha(dest/Path(n).name)
 meta['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ipfiles+[image]};meta['generator_sha256']=sha(Path(__file__));meta['scope']='Banked BTB + compact side payload + correct asymmetric IP + balanced encoded producer selection'
 (dest/'generation.json').write_text(json.dumps(meta,indent=2)+'\n');print('GENERATED',dest.name)
if __name__=='__main__':main()
