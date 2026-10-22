"""Parallel range qualification for sign-extended load offsets; same requests."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/load_bp_dual_boundary_storemmio';out=src.with_name('load_bp_dual_boundary_storeprefix');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_core.v';s=p.read_text();needle=' wire[31:0] direct_agu=ex_packet[135:104]+ex_packet[71:40];';assert s.count(needle)==1
 s=s.replace(needle,''' // A load has a signed 12-bit offset. Qualify its result region using
 // an 8-bit carry, parallel middle-group generate/propagate, and base
 // prefix comparisons. Do not wait for the full 32-bit AGU carry before CE.
 function local_load_address;
  input[31:0] base;input[11:0] offset;
  reg[8:0] lo;reg[4:0] mid;reg c12,c15,c16,sgn,bit15,same_hi;
  reg code_hi,data_hi;
  begin
   lo={1'b0,base[7:0]}+{1'b0,offset[7:0]};
   mid={1'b0,base[11:8]}+{1'b0,offset[11:8]};
   c12=mid[4] || ((&(base[11:8]^offset[11:8])) && lo[8]);
   sgn=offset[11];
   c15=sgn ? ((|base[14:12]) || c12) : ((&base[14:12]) && c12);
   c16=sgn ? ((|base[15:12]) || c12) : ((&base[15:12]) && c12);
   bit15=base[15]^sgn^c15;same_hi=(c16==sgn);
   code_hi=(same_hi && base[31:16]==16'h0000) ||
           (!sgn && c16 && base[31:16]==16'hffff) ||
           (sgn && !c16 && base[31:16]==16'h0001);
   data_hi=(same_hi && base[31:16]==16'h1000) ||
           (!sgn && c16 && base[31:16]==16'h0fff) ||
           (sgn && !c16 && base[31:16]==16'h1001);
   local_load_address=code_hi || (data_hi && !bit15);
  end
 endfunction
 wire direct_local=local_load_address(ex_packet[135:104],ex_packet[51:40]);
 wire queued_local=compact_packet[52:21]<32'h00010000 ||
                  (compact_packet[52:21]>=32'h10000000 && compact_packet[52:21]<32'h10008000);
 wire launch_local=queued_valid ? queued_local : direct_local;
'''+needle)
 needle='.launch_address(launch_address),.write_address(d_write_addr)';assert s.count(needle)==1;s=s.replace(needle,'.launch_address(launch_address),.launch_local(launch_local),.write_address(d_write_addr)');p.write_text(s)
 p=out/'nc_memory.v';s=p.read_text();needle='input wire[31:0] launch_address,output wire[31:0] write_address';assert s.count(needle)==1;s=s.replace(needle,'input wire[31:0] launch_address,input wire launch_local,output wire[31:0] write_address');needle="wire input_local=launch_address<32'h00010000 || (launch_address>=32'h10000000 && launch_address<32'h10008000);";assert s.count(needle)==1;s=s.replace(needle,'wire input_local=launch_local;');p.write_text(s)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope='Same storemmio schedule; SAT-checked parallel load range qualification, full address unchanged; queued qualifier from saved address; research not adopted')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED dual_boundary_storeprefix')
if __name__=='__main__':main()
