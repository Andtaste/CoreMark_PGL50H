"""Predecode forwarding write qualifiers at the existing MEM/WB boundary."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 accepted=ROOT/'docs/accepted_dual_baseline.json';d=json.loads(accepted.read_text());assert d['variant']=='dual_boundary_storewrite';src=ROOT/d['source_directory'];out=src.with_name('load_bp_dual_boundary_wbflags');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v');p=out/'nc_core.v';s=p.read_text();s=rep(s,' wire[64:0] w_side;wire commit=wb_valid && !w_fault;', ' reg wb_forward0,wb_forward1;\n wire[64:0] w_side;wire commit=wb_valid && !w_fault;');s=rep(s,'.w1_valid(commit1 && w1_rd!=0)', '.w1_valid(commit && wb_forward1)');s=rep(s,'.w_valid(commit && w_wr && w_rd!=0)', '.w_valid(commit && wb_forward0)');s=rep(s,' always @(posedge clk) if(memory_done) begin wb_q<=memory_packet;wb_side_q<=memory_side;end', ''' // Write eligibility is metadata already held in MEM. Capture two local
 // qualifier bits alongside the existing WB packet; no new stage/cycle.
 always @(posedge clk) if(memory_done) begin
  wb_q<=memory_packet;wb_side_q<=memory_side;
  wb_forward0<=memory_packet[3] && memory_packet[15:11]!=0;
  wb_forward1<=memory_side[64] && !memory_side[38] && memory_side[43:39]!=0;
 end''');p.write_text(s)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']};g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),accepted_dual_sha256=sha(accepted),scope='Independent accepted storewrite successor: predecode two WB forwarding eligibility metadata bits at existing MEM/WB capture; no bank-request, multiplier, pairing, FIFO or cycle change; not adopted');(out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED dual_boundary_wbflags')
if __name__=='__main__':main()
