"""Remove duplicated dual-BTB storage and redundant secondary PC payload.
Optional asymmetric Pango TDP configuration replaces full RAM mirrors.
Production and the previous trial are immutable.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--wide',action='store_true');args=ap.parse_args()
 src=ROOT/'simulation/results/load_bp_dual_issue_predecode';dest=src.with_name('load_bp_dual_ram'+('_wide' if args.wide else ''));dest.mkdir(exist_ok=True)
 meta=json.loads((src/'generation.json').read_text())
 for n,h in meta['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h,n;shutil.copyfile(p,dest/p.name)
 # Both queried words belong to different PC[2] banks. A query beginning
 # in the high half consumes one word only; its unused second prediction
 # need not read the next group. Training writes exactly one bank.
 btb=(ROOT/'hardware/pds/source/core/nc_btb.v').read_text().replace('module nc_btb(','module nc_btb_bank(')
 btb=btb.replace('reg[63:0] valid;','reg[31:0] valid;').replace('[0:63]','[0:31]')
 btb=rep(btb,'wire[5:0] r=lookup_pc[7:2],w=update_pc[7:2];','wire[4:0] r=lookup_pc[7:3],w=update_pc[7:3];')
 btb=btb.replace('// 64 direct-mapped entries. Full PC tag [31:8], word target.',
  '// One PC[2] bank of the same 64-entry BTB: 32 entries, full PC[31:8] tag.')
 (dest/'nc_btb.v').write_text(btb);meta['override_sha256']['hardware\\pds\\source\\core\\nc_btb.v']=sha(dest/'nc_btb.v')
 p=dest/'nc_fetch.v';s=p.read_text()
 s=rep(s,'generate if(ENABLE_BP) begin:predictor','''wire[31:0] even_prediction,odd_prediction;
 wire[31:0] even_pc={next_pc[31:3],3'b000},odd_pc={next_pc[31:3],3'b100};
 generate if(ENABLE_BP) begin:predictor''')
 s=rep(s,'nc_btb btb(', 'nc_btb_bank btb(');s=rep(s,'nc_btb btb1(', 'nc_btb_bank btb1(')
 s=rep(s,'.lookup_pc(next_pc),.prediction(lookup_prediction)', '.lookup_pc(even_pc),.prediction(even_prediction)')
 s=rep(s,'.lookup_pc(lookup_pc1),.prediction(lookup_prediction1)', '.lookup_pc(odd_pc),.prediction(odd_prediction)')
 needle='.update_valid(bp_update_valid),.update_branch(bp_update_branch)';assert s.count(needle)==2
 s=s.replace(needle,'.update_valid(bp_update_valid && !bp_update_pc[2]),.update_branch(bp_update_branch)',1)
 s=s.replace(needle,'.update_valid(bp_update_valid && bp_update_pc[2]),.update_branch(bp_update_branch)',1)
 s=rep(s,'end else begin:no_predictor','''assign lookup_prediction=next_pc[2] ? odd_prediction : even_prediction;
  assign lookup_prediction1=odd_prediction;
 end else begin:no_predictor''')
 p.write_text(s)
 p=dest/'nc_core.v';s=p.read_text().replace('[101:0]','[64:0]').replace('w_side[101]','w_side[64]')
 s=rep(s,'wire[31:0] w1_pc=w_side[100:69],w1_insn=w_side[68:37],w1_result=w_side[36:5];',
  'wire[31:0] w1_pc=w_next,w1_insn=w_side[63:32],w1_result=w_side[31:0];')
 s=rep(s,'wire[4:0] w1_rd=w_side[4:0];','wire[4:0] w1_rd=w1_insn[11:7];')
 s=rep(s,'{side_execute,secondary_result[276:213],secondary_result[180:149],secondary_result[15:11]}',
  '{side_execute,secondary_result[244:213],secondary_result[180:149]}')
 s=rep(s,'nc_fifo #(.WIDTH(286),.DEPTH(4))','nc_fifo #(.WIDTH(249),.DEPTH(4))')
 s=s.replace('// Compact only mutually exclusive fields', '// Secondary PC equals primary sequential next-PC; rd comes from its instruction.\n // This removes 37 stored bits without an extra EX adder or any new bypass.\n // Compact only mutually exclusive fields')
 p.write_text(s)
 p=dest/'nc_memory.v';p.write_text(p.read_text().replace('[101:0]','[64:0]'))
 if args.wide:
  # Same bits, grouped into A-port-width initialization words. Reconstruct
  # the complete original image and assert byte identity before IP generation.
  boot=ROOT/'sw/build/boot.hex';words=boot.read_text().split();assert len(words)==16384
  image=dest/'boot64.hex';image.write_text(''.join(words[i+1].zfill(8)+words[i].zfill(8)+'\n' for i in range(0,len(words),2)))
  reconstructed=[]
  for line in image.read_text().split():reconstructed.extend([line[8:],line[:8]])
  assert [int(w,16) for w in reconstructed]==[int(w,16) for w in words]
  ipfiles=[]
  for name,addr in (('ram1_tdp',13),('ram2_tdp',12)):
   original=ROOT/f'hardware/pds/ipcore/{name}/{name}.idf';folder=dest/'ipcore'/name;folder.mkdir(parents=True,exist_ok=True);path=folder/(name+'.idf')
   tree=ET.parse(original);params={'A_ADDR_WIDTH':str(addr),'A_DATA_WIDTH':'64','A_BE_WIDTH':'8','SAMEWIDTH_EN':'false'}
   if name=='ram1_tdp':params.update(INIT_FILE=image.as_posix(),INIT_FORMAT='HEX')
   for item in tree.findall('.//param'):
    n=item.findtext('name')
    if n in params:item.find('value').text=params[n]
   for pin in tree.findall('.//pin'):
    n=pin.findtext('name')
    if n in ('a_addr','a_wr_data','a_rd_data','a_wr_byte_en'):pin.find('msb').text=str(addr-1 if n=='a_addr' else 7 if n=='a_wr_byte_en' else 63)
   tree.write(path,encoding='utf-8',xml_declaration=True)
   with (folder/'regenerate.log').open('wb') as f:x=subprocess.run([r'E:\pango\PDS_2022.2-SP1-Lite\bin\ip_generate.exe','-i',str(path),'-disable-syn'],cwd=folder,stdout=f,stderr=subprocess.STDOUT,timeout=180)
   assert x.returncode==0,(name,(folder/'regenerate.log').read_text(errors='replace')[-3000:])
   generated=(folder/(name+'.v')).read_text()
   assert 'A_DATA_WIDTH = 64' in generated and 'B_DATA_WIDTH = 32' in generated
   ipfiles.extend(p for p in folder.rglob('*') if p.is_file() and p.suffix in ('.idf','.v'))
  p=dest/'nc_local_bus.v';s=p.read_text()
  s=rep(s,'wire[31:0] iq0,iq1,iq0_hi,iq1_hi,dq0,dq1;', 'wire[63:0] iq0,iq1;wire[31:0] dq0,dq1;')
  s=rep(s,'assign idata=ibank ? {iq1_hi,iq1} : {iq0_hi,iq0};','assign idata=ibank ? iq1 : iq0;')
  for name in ('code','data'):
   start=s.index(' ram'+('1' if name=='code' else '2')+'_tdp ram_'+name+'_hi(');end=s.index('));',start)+3;s=s[:start]+s[end:]
  s=s.replace('.a_addr(ia_lo[15:2])','.a_addr(ia[15:3])').replace('.a_addr(ia_lo[14:2])','.a_addr(ia[14:3])')
  s=s.replace('.a_wr_data(32\'b0)', '.a_wr_data(64\'b0)').replace('.a_wr_byte_en(4\'b0)', '.a_wr_byte_en(8\'b0)')
  p.write_text(s)
  # Functional model kept separate from synthesis IP. A and B share the
  # same 32-bit word store, so B writes are immediately coherent for A.
  model='// Functional asymmetric TDP model; synthesized design uses generated Pango IP.\n'
  for name,a,b,count,init in (('ram1_tdp',13,14,16384,True),('ram2_tdp',12,13,8192,False)):
   model+=f'''module {name}(input wire a_clk,a_rst,a_clk_en,a_wr_en,input wire[{a-1}:0] a_addr,
 input wire[63:0] a_wr_data,input wire[7:0] a_wr_byte_en,output reg[63:0] a_rd_data,
 input wire b_clk,b_rst,b_clk_en,b_wr_en,input wire[{b-1}:0] b_addr,
 input wire[31:0] b_wr_data,input wire[3:0] b_wr_byte_en,output reg[31:0] b_rd_data);
 reg[31:0] mem[0:{count-1}];integer i,j,k;reg[4095:0] image;
 initial begin
  for(i=0;i<{count};i=i+1) mem[i]=0;
'''+('  if($value$plusargs("image=%s",image)) $readmemh(image,mem);\n' if init else '')+'''
 end
 always @(posedge a_clk) if(a_clk_en) begin
  a_rd_data<={mem[{a_addr,1'b1}],mem[{a_addr,1'b0}]};
  for(j=0;j<8;j=j+1) if(a_wr_en && a_wr_byte_en[j]) mem[{a_addr,1'b0}+(j/4)][8*(j%4)+:8]<=a_wr_data[8*j+:8];
 end
 always @(posedge b_clk) if(b_clk_en) begin
  b_rd_data<=mem[b_addr];for(k=0;k<4;k=k+1) if(b_wr_en && b_wr_byte_en[k]) mem[b_addr][8*k+:8]<=b_wr_data[8*k+:8];
 end
endmodule
'''
  (dest/'pango_ram_wide_models.v').write_text(model)
  meta['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ipfiles+[image]}
 for n in meta['override_sha256']:meta['override_sha256'][n]=sha(dest/Path(n).name)
 meta['generator_sha256']=sha(Path(__file__));meta['parent_generation_sha256']=sha(src/'generation.json');meta['scope']='PC[2]-banked BTB64, compact secondary payload'+('; asymmetric A64/B32 Pango TDP' if args.wide else '')
 (dest/'generation.json').write_text(json.dumps(meta,indent=2)+'\n');print('GENERATED',dest.name)
if __name__=='__main__':main()
