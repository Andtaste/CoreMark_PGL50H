"""Separate early load AGU and registered write-hazard addresses from reused aux."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 src=ROOT/'simulation/results/load_bp_dual_boundary_read';out=src.with_name('load_bp_dual_boundary_launch');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_core.v';s=p.read_text();s=rep(s,' output wire d_req_valid,input wire d_req_ready,output wire[31:0] d_addr,d_wdata,',' output wire d_req_valid,input wire d_req_ready,output wire[31:0] d_addr,d_wdata,\n output wire[31:0] d_write_addr,')
 s=rep(s,' wire direct_take=!queued_valid && execute_valid && memory_ready;',''' wire direct_take=!queued_valid && execute_valid && memory_ready;
 // Separate request address from the compact auxiliary field. Branch next-PC
 // is a valid auxiliary value, but must not drive the early load address cone.
 wire[31:0] direct_agu=ex_packet[135:104]+ex_packet[71:40];
 wire[31:0] launch_address=queued_valid ? compact_packet[52:21] : direct_agu;
''')
 s=rep(s,'.packet(mem_packet),\n  .mul_tag', '.packet(mem_packet),.launch_address(launch_address),.write_address(d_write_addr),\n  .mul_tag');p.write_text(s)
 p=out/'nc_memory.v';s=p.read_text();s=rep(s,' input wire[279:0] packet,output wire wb_valid,', ' input wire[31:0] launch_address,output wire[31:0] write_address,input wire[279:0] packet,output wire wb_valid,');s=rep(s,"wire input_local=input_address<32'h00010000 || (input_address>=32'h10000000 && input_address<32'h10008000);", "wire input_local=launch_address<32'h00010000 || (launch_address>=32'h10000000 && launch_address<32'h10008000);");s=rep(s,'wire[31:0] request_address=use_input ? input_address : address;', 'wire[31:0] request_address=use_input ? launch_address : address;');s=rep(s,' assign mul_tag=tag;', ' assign write_address=address;\n assign mul_tag=tag;');s=rep(s,'assign req_write=old_request && kind==5;', 'assign req_write=!kill && old_request && kind==5;');p.write_text(s)
 p=out/'nc_soc.v';s=p.read_text();s=rep(s,'wire[31:0] ia,da,dw,ddata;','wire[31:0] ia,da,dw,ddata,wa;');s=rep(s,'.d_req_valid(dv),.d_req_ready(dr),','.d_write_addr(wa),.d_req_valid(dv),.d_req_ready(dr),');s=rep(s,'.dv(dv),.dr(dr),.da(da),','.dv(dv),.dr(dr),.wa(wa),.da(da),');p.write_text(s)
 p=out/'nc_local_bus.v';s=p.read_text();s=rep(s,'input wire[31:0] da,dw,','input wire[31:0] da,dw,wa,');s=rep(s,"wire uart_addr=da==32'h20000000;", "wire uart_addr=wa==32'h20000000;");s=rep(s,'wire collision=da_fire && dwrite && ((ib0 && db0)||(ib1 && db1)) && ia[15:3]==da[15:3];', '''// dwrite is a published-write qualifier: it implies dv. Its address is
 // registered in MEM, so EX load/branch data cannot enter IF collision control.
 wire wb0=wa<32'h00010000,wb1=wa>=32'h10000000 && wa<32'h10008000;
 wire collision=dr && dwrite && ((ib0 && wb0)||(ib1 && wb1)) && ia[15:3]==wa[15:3];''');p.write_text(s)
 for name in ('nc_core.v','nc_memory.v','nc_soc.v','nc_local_bus.v'):
  for key in g['override_sha256']:
   if Path(key).name==name:g['override_sha256'][key]=sha(out/name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope='dual_boundary_launch; identical read-only early launch schedule, dedicated AGU address and registered MEM store hazard address; qualified writes imply valid; no raw RAM/EX return; not adopted')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED dual_boundary_launch')
if __name__=='__main__':main()
