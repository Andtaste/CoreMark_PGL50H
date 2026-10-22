"""Partition measured operand-head pointer loads without extra latency."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 accepted=ROOT/'docs/accepted_dual_baseline.json';d=json.loads(accepted.read_text());assert d['variant']=='dual_boundary_storewrite'
 src=ROOT/d['source_directory'];out=src.with_name('load_bp_dual_boundary_headlocal');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_operands.v';s=p.read_text();s=rep(s,' reg[223:0] side[0:1];',''' // Same next-state function as rd, captured on the same edge. Keep six
 // physical destination copies for primary metadata, secondary metadata,
 // and four 32-bit operands. Occupancy/availability keep the original rd.
 reg[5:0] local_rd /* synthesis syn_preserve=1 */;
 reg[223:0] side[0:1];''')
 s=s.replace('side[rd][223:136]','side[local_rd[1]][223:136]').replace('side[rd][71:0]','side[local_rd[1]][71:0]')
 s=s.replace('selected_c[rd]','selected_c[local_rd[4]]').replace('selected_d[rd]','selected_d[local_rd[5]]')
 s=s.replace('selected_va[rd]','selected_va[local_rd[2]]').replace('selected_vb[rd]','selected_vb[local_rd[3]]')
 s=s.replace('controls[rd]','controls[local_rd[0]]').replace('predictions[rd]','predictions[local_rd[0]]').replace('token[rd]','token[local_rd[0]]').replace('payload[rd]','payload[local_rd[0]]')
 s=rep(s,' wire push=in_valid && in_ready,pop=out_valid && out_ready;',''' wire push=in_valid && in_ready,pop=out_valid && out_ready;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) local_rd<=0;
  else if(clear) local_rd<=0;
  else local_rd<={6{pop ? !rd : rd}};
 end''');p.write_text(s)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),accepted_dual_sha256=sha(accepted),scope='Independent accepted storewrite successor: six same-edge preserved read-head pointer copies partition operand/metadata output mux loads; original source muxes, priority, readiness/capacity, capture, and all cycles retained. Neither headmux nor pcselect included; not adopted')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED dual_boundary_headlocal')
if __name__=='__main__':main()
