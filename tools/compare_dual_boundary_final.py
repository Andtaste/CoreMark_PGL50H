"""Honor old IF's two adjacent words from any aligned word address."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 base=ROOT/'tools/compare_dual_boundary_old_v3.py';s=base.read_text()
 needle='  corefiles=[]' # Directory substitution is inside the generated runner.
 s=s.replace("s=base.read_text().replace(\"('old','fifo','slot','early')\",\"('old','fifo','slot','early','read')\")", "s=base.read_text().replace(\"('old','fifo','slot','early')\",\"('old','fifo','slot','early','read')\").replace('dual_boundary_common','dual_boundary_common_final')")
 needle=" bus=out/'nc_local_bus_common.v';bus.write_text(bs);inputs +=[original_bus]"
 verilog=" reg[63:0] common_fetch;\n wire[13:0] first0=WORD_FETCH ? ia[15:2] : {ia[15:3],1'b0};\n wire[12:0] first1=WORD_FETCH ? ia[14:2] : {ia[14:3],1'b0};\n always @(posedge clk) if(ia_fire) begin\n  if(ib0) common_fetch<={ram_code.mem[first0+14'd1],ram_code.mem[first0]};\n  else if(ib1) common_fetch<={ram_data.mem[first1+13'd1],ram_data.mem[first1]};\n  else common_fetch<=0;\n end\n"
 repl=" bs=bs.replace('SECOND_PORT=1)', 'SECOND_PORT=1,WORD_FETCH='+str(int(a.target=='old'))+')')\n bs=bs.replace('assign idata=ibank ? iq1 : iq0;','assign idata=common_fetch;').replace(' reg mmio_known;',"+repr(verilog)+"+' reg mmio_known;')\n"+needle
 marker=' assert s.count(needle)==1;s=s.replace(needle,code+needle)'
 assert s.count(marker)==1
 s=s.replace(marker, ' code=code.replace('+repr(needle)+','+repr(repl)+')\n'+marker)
 s=s.replace("p=ROOT/('simulation/results/dual_boundary_common/'+v+'/result.json')", "p=ROOT/('simulation/results/dual_boundary_common_final/'+v+'/result.json')")
 s=s.replace(" ns={'__file__':str(base),'__name__':'common_v3'};",' s=s.replace("uartlog=out/(phase+\'_uart.txt\');inputs.append(image)","original_image=image;words=[int(w,16) for w in image.read_text().split()];patches=[]\\n  for i,word in enumerate(words):\\n   if word&127==115 and (word>>12)&7==2 and word>>20 in (0x7cb,0x7cc,0x7cd,0x7ce):\\n    patches.append(dict(pc=i*4,old=word));words[i]=((word>>7)&31)<<7|0x13\\n  assert len(patches)==4,patches\\n  image=out/(phase+\'_common.hex\');image.write_text(\'\'.join(f\'{word:08x}\\\\n\' for word in words));(out/(phase+\'_patches.json\')).write_text(json.dumps(patches,indent=2)+\'\\\\n\')\\n  uartlog=out/(phase+\'_uart.txt\');inputs +=[original_image,image]")\n ns={\'__file__\':str(base),\'__name__\':\'common_v3\'};')
 ns={'__file__':str(base),'__name__':'common_v4'};exec(compile(s,str(base),'exec'),ns);ns['main']()
 v=sys.argv[sys.argv.index('--target')+1];p=ROOT/('simulation/results/dual_boundary_common_final/'+v+'/result.json');x=json.loads(p.read_text());x['scope']='Same diagnostic-adapted binary on all targets: four unsupported old CSR reads after the stats stop are replaced with zero; benchmark instructions unchanged. Common synchronous behavioral word memory with per-CPU fetch protocol adapter and atomic old LSU acceptance. Not an original SoC or physical A64 RAM comparison.';x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
