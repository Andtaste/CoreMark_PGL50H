"""Publish equivalent per-bank RAM requests; optional local carry-select AGU."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_boundary_bankreq','dual_boundary_bankagu'),required=True);a=ap.parse_args();accepted=ROOT/'docs/accepted_dual_baseline.json';d=json.loads(accepted.read_text());assert d['variant']=='dual_boundary_storewrite';src=ROOT/d['source_directory'];out=src.with_name('load_bp_'+a.variant);assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_memory.v';s=p.read_text();s=rep(s,' input wire[31:0] launch_address,',' output wire[1:0] req_banks,\n input wire[31:0] launch_address,');s=rep(s,' assign req_addr=request_address;', ''' // Publish each local-bank request before merging the generic bus valid
 // and old/early address selection. These qualifiers imply req_valid and
 // the matching req_addr bank; they never depend on req_ready.
 wire bank_early=EARLY_REQUEST && can_accept && valid && input_memory && packet[7:4]==4 && !old_request && response_credit;
 wire[1:0] held_banks={(address>=32'h10000000 && address<32'h10008000),address<32'h00010000};
 wire[1:0] launch_banks={(launch_address>=32'h10000000 && launch_address<32'h10008000),launch_address<32'h00010000};
 assign req_banks={2{!kill}} & (({2{old_request}} & held_banks) | ({2{bank_early}} & launch_banks));
 assign req_addr=request_address;''');p.write_text(s)
 p=out/'nc_core.v';s=p.read_text();s=rep(s,' output wire[31:0] d_write_addr,',' output wire[1:0] d_ram_requests,\n output wire[31:0] d_write_addr,');s=rep(s,'.launch_address(launch_address),.write_address(d_write_addr)', '.launch_address(launch_address),.req_banks(d_ram_requests),.write_address(d_write_addr)')
 if a.variant.endswith('bankagu'):
  s=rep(s,' wire[31:0] direct_agu=ex_packet[135:104]+ex_packet[71:40];',''' // Same 32-bit modular sum. Compute both upper-half carries in parallel;
 // this changes the local datapath only, with no cycle or issue change.
 function[31:0] fast_address;
  input[31:0] base,offset;reg[16:0] lo;reg[15:0] hi0,hi1;
  begin
   lo={1'b0,base[15:0]}+{1'b0,offset[15:0]};
   hi0=base[31:16]+offset[31:16];hi1=base[31:16]+offset[31:16]+16'd1;
   fast_address={lo[16] ? hi1 : hi0,lo[15:0]};
  end
 endfunction
 wire[31:0] direct_agu=fast_address(ex_packet[135:104],ex_packet[71:40]);''')
 p.write_text(s)
 p=out/'nc_soc.v';s=p.read_text();s=rep(s,' wire iv,ir,iov,ior,ie,dv,dr,dov,dor,de,dwrite,timer_irq;', ' wire[1:0] ram_requests;\n wire iv,ir,iov,ior,ie,dv,dr,dov,dor,de,dwrite,timer_irq;');s=rep(s,'.d_write_addr(wa),', '.d_ram_requests(ram_requests),.d_write_addr(wa),');s=rep(s,'nc_local_bus #(.CLOCK_HZ(CLOCK_HZ))', 'nc_local_bus #(.CLOCK_HZ(CLOCK_HZ),.USE_RAM_REQUESTS(1))');s=rep(s,'.dv(dv),.dr(dr),', '.ram_requests(ram_requests),.dv(dv),.dr(dr),');p.write_text(s)
 p=out/'nc_local_bus.v';s=p.read_text();s=rep(s,'parameter CLOCK_HZ=75000000)', 'parameter CLOCK_HZ=75000000,USE_RAM_REQUESTS=0)');s=rep(s,' input wire dv,', ' input wire[1:0] ram_requests,\n input wire dv,');s=rep(s,' wire da_fire=dv && dr;', ''' wire da_fire=dv && dr;
 // Default preserves the generic standalone bus interface. The fixed SoC
 // enables SAT-checked request-bank qualifiers published by MEM.
 wire ram0_ce=USE_RAM_REQUESTS ? (dr && ram_requests[0]) : (da_fire && db0);
 wire ram1_ce=USE_RAM_REQUESTS ? (dr && ram_requests[1]) : (da_fire && db1);''');s=rep(s,'.b_clk_en(da_fire && db0)', '.b_clk_en(ram0_ce)');s=rep(s,'.b_clk_en(da_fire && db1)', '.b_clk_en(ram1_ce)');p.write_text(s)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']};g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),accepted_dual_sha256=sha(accepted),scope='Equivalent per-bank qualified RAM enable; fixed SoC uses published qualifiers, standalone bus default unchanged; optional carry-select direct AGU; no pipeline cycle or IPC policy change; not adopted')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',a.variant)
if __name__=='__main__':main()
