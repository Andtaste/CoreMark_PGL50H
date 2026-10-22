"""Isolated redundant write control removal, then bit-prefix range decode."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_boundary_storewrite','dual_boundary_storelogic'),required=True);a=ap.parse_args()
 src=ROOT/'simulation/results/load_bp_dual_boundary_storeack';out=src.with_name('load_bp_'+a.variant);assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 assert sha(ROOT/'docs/accepted_dual_baseline.json')==g['accepted_dual_sha256']
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_local_bus.v';s=p.read_text();s=rep(s,'    if(dwrite) begin','''   end else if(dov && dor) dpending<=0;
   // dwrite is published only for a valid held MEM store. Do not put the
   // early-load valid/range cone in series with these write side effects.
   if(dwrite && dr) begin''');s=rep(s,'for(j=0;j<4;j=j+1) if(dm[j]) case(da)','for(j=0;j<4;j=j+1) if(dm[j]) case(wa)');s=rep(s,"if(da==32'h20002000 && dm[0])", "if(wa==32'h20002000 && dm[0])");s=rep(s,'    end\n   end else if(dov && dor) dpending<=0;','   end');p.write_text(s)
 if a.variant.endswith('storelogic'):
  p=out/'nc_memory.v';s=p.read_text();s=rep(s,"address<32'h00010000 || (address>=32'h10000000 && address<32'h10008000)","address[31:16]==16'h0000 || address[31:15]==17'h02000");s=rep(s,"launch_address<32'h00010000 || (launch_address>=32'h10000000 && launch_address<32'h10008000)","launch_address[31:16]==16'h0000 || launch_address[31:15]==17'h02000");s=rep(s,'wire posted_fire=!kill && store_fast && old_request && req_ready;', 'wire posted_fire=POST_LOCAL_STORES && req_write && req_ready && local_write_address;');s=rep(s,'wire early_request=EARLY_REQUEST && can_accept && valid && input_memory && packet[7:4]==4 && input_local && !old_request && response_credit;', 'wire early_request=EARLY_REQUEST && can_accept && valid && !packet[2] && packet[7:4]==4 && input_local && !old_request && response_credit;')
  s=rep(s,' wire store_fast=POST_LOCAL_STORES && memory_pending && kind==5 && local_write_address;\n','');s=rep(s,' wire[31:0] request_data=use_input ? packet[116:85] : store_data;\n','');s=rep(s,' wire[2:0] request_f3=use_input ? packet[10:8] : f3;\n','');p.write_text(s)
  p=out/'nc_local_bus.v';s=p.read_text()
  for addr in ('ia','da','wa'):
   s=rep(s,addr+"<32'h00010000",addr+"[31:16]==16'h0000");s=rep(s,addr+">=32'h10000000 && "+addr+"<32'h10008000",addr+"[31:15]==17'h02000")
  p.write_text(s)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope='Isolated storeack successor: MMIO write enable uses published held-write handshake, write decode uses held address; optional exact bit-prefix ranges and redundant predicates removed; no extra cycle or adoption')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',a.variant)
if __name__=='__main__':main()
