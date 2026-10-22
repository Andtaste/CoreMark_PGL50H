"""BTB bank equivalence, exhaustive producer tags and actual generated IP."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'simulation/results/load_bp_dual_ram_logic'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 dest=OUT/'equivalence';dest.mkdir(exist_ok=True);iv=ROOT.parent/'tmp/iverilog-portable/bin/iverilog.exe';vvp=iv.with_name('vvp.exe');inputs=[Path(__file__).resolve()];tests=[]
 def run(cmd,name):
  p=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,timeout=180);(dest/name).write_bytes(p.stdout+p.stderr)
  assert p.returncode==0,(name,(p.stdout+p.stderr)[-3000:]);return p.stdout.decode(errors='replace')
 unit=ROOT/'simulation/research/dual_ram/btb_banks_tb.v';rtl=[ROOT/'hardware/pds/source/core/nc_btb.v',OUT/'nc_btb.v'];inputs+=[unit,*rtl]
 run([iv,'-g2012','-s','btb_banks_tb','-o',dest/'bank.vvp',*rtl,unit],'bank_compile.log')
 t=run([vvp,dest/'bank.vvp'],'bank.log');assert 'PASS BTB banks updates=30000' in t;tests.append(t.strip())
 core=OUT/'nc_core.v';s=core.read_text();function=s[s.index(' function [3:0] newest4;'):s.index(' endfunction')+len(' endfunction')]
 encoder=dest/'producer_encoder_tb.v';encoder.write_text('''`timescale 1ns/1ps
module producer_encoder_tb;
'''+function+'''
 reg[15:0] mask,below;reg[3:0] actual,expected;integer m,tail,g,n,cases=0;
 initial begin
  for(m=0;m<65536;m=m+1) for(tail=0;tail<8;tail=tail+1) begin
   mask=m;below=0;expected=0;
   for(n=0;n<8;n=n+1) begin
    if(n<tail) below[2*n+:2]=2'b11;
    g=(tail+n)&7;
    if(mask[2*g] || mask[2*g+1]) expected=mask[2*g+1] ? 2*g+1 : 2*g;
   end
   actual=|(mask & below) ? newest4(mask & below) : newest4(mask);
   if(actual!==expected) $fatal(1,"Producer tag differs mask=%h tail=%0d actual=%0d expected=%0d",mask,tail,actual,expected);
   cases=cases+1;
  end
  $display("PASS balanced encoded producer identity cases=%0d",cases);$finish;
 end
endmodule
''');inputs+=[core,encoder]
 run([iv,'-g2012','-s','producer_encoder_tb','-o',dest/'encoder.vvp',encoder],'encoder_compile.log')
 t=run([vvp,dest/'encoder.vvp'],'encoder.log');assert 'PASS balanced encoded producer identity cases=524288' in t;tests.append(t.strip())
 library=Path('E:/pango/PDS_2022.2-SP1-Lite/arch/vendor/pango/verilog/simulation/GTP_DRM18K.v')
 source=ROOT/'simulation/research/dual_ram/wide_ip_tb.v';inputs+=[source,ROOT/'sw/build/boot.hex']
 for name in ('ram1_tdp','ram2_tdp'):
  folder=OUT/'ipcore'/name;ip=[folder/(name+'.v'),folder/'rtl'/('ipml_dpram_v1_6_'+name+'.v')]
  tb=source
  if name=='ram2_tdp':
   tb=dest/'wide_data_ip_tb.v';s=source.read_text()
   s=s.replace('ram1_tdp ram(','ram2_tdp ram(').replace('reg[12:0] aa=0;reg[13:0] ba=0;','reg[11:0] aa=0;reg[12:0] ba=0;')
   s=s.replace('reference[0:16383]','reference[0:8191]').replace('$readmemh(image,reference);','for(i=0;i<8192;i=i+1) reference[i]=0;')
   s=s.replace('i<8192','i<4096').replace('for(i=0;i<4096;i=i+1) reference[i]=0;','for(i=0;i<8192;i=i+1) reference[i]=0;')
   s=s.replace("aa=13'h1555;ba=14'h2aaa", "aa=12'h555;ba=13'h1aaa")
   s=s.replace('aa=rng[12:0];ba=rng[26:13]','aa=rng[11:0];ba=rng[24:12]').replace('ba[13:1]','ba[12:1]')
   tb.write_text(s)
  inputs+=ip+[folder/'rtl'/(name+'_init_param.v'),folder/(name+'.idf'),tb]
  run([iv,'-g2012','-s','wide_ip_tb','-I',folder/'rtl','-o',dest/(name+'.vvp'),*ip,library,tb],name+'_compile.log')
  t=run([vvp,dest/(name+'.vvp'),'+image='+str(ROOT/'sw/build/boot.hex')],name+'.log')
  assert 'PASS generated A64/B32 IP initialization/bytewrites/coherence' in t;tests.append(name+' '+t.strip())
 # The unchanged queue credit and registered datapath boundaries are part
 # of the acceptance contract. This structural check is not a timing proof.
 for marker in ('wire ex_fire=execute_valid && mem_credit;', '.out_valid(execute_valid),.out_ready(mem_credit)',
                '.out_valid(ex_valid),.out_ready(ex_pop)', 'f1_tag=f_tag','nc_fifo #(.WIDTH(249),.DEPTH(4))'):
  assert marker in core.read_text(),marker
 assert 'early_offer' not in core.read_text() and 'tag_a[0]=match_a1[tag_a[3:1]]' not in core.read_text()
 inputs+=[OUT/'nc_memory.v',OUT/'nc_operands.v']
 assert 'assign in_ready=count!=2' in (OUT/'nc_operands.v').read_text()
 tests.append('PASS redundancy/boundary audit: encoded comparison retained; no EX/RAM bypass; registered queue credit')
 result=dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs},external_library_sha256={str(library):sha(library)})
 (dest/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('\n'.join(tests))
if __name__=='__main__':main()
