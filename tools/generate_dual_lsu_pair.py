"""Permit simultaneous stores only after an explicit fault-free RAM grant."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 src=ROOT/'simulation/results/load_bp_dual_lsu_forward';out=src.with_name('load_bp_dual_lsu_pair');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_core.v';s=p.read_text();s=rep(s,'output wire d_req_valid,input wire d_req_ready,','output wire d_req_valid,input wire d_req_ready,input wire d_req_nofault,');s=rep(s,'.req_valid(d_req_valid),','.req_nofault(d_req_nofault),.req_valid(d_req_valid),');p.write_text(s)
 p=out/'nc_memory.v';s=p.read_text();s=rep(s,'output wire req_valid,input wire req_ready,','output wire req_valid,input wire req_ready,input wire req_nofault,');s=rep(s,'reg p_sent,s_sent,p_done,s_done,p_error,s_offered;','reg p_sent,s_sent,p_done,s_done,p_error,s_offered,p_guaranteed;')
 s=rep(s,'wire side_authorized=!(ss || alias_line) || !primary_waiting || primary_safe;','''wire guaranteed_primary=(can_start ? 1'b0 : p_guaranteed) || (p_fire && req_nofault);
 wire side_authorized=!(ss || alias_line) || !primary_waiting || primary_safe ||
                           (!alias_line && guaranteed_primary);''')
 s=rep(s,'if(p_fire) p_sent<=1;','if(p_fire) begin p_sent<=1;p_guaranteed<=req_nofault;end')
 s=rep(s,'p_sent<=p_fire;s_sent<=s_fire;s_offered<=req1_valid;','p_sent<=p_fire;s_sent<=s_fire;s_offered<=req1_valid;p_guaranteed<=p_fire && req_nofault;');p.write_text(s)
 p=out/'nc_local_bus.v';s=p.read_text();s=rep(s,'input wire dv,output wire dr,','input wire dv,output wire dr,output wire d_nofault,');s=rep(s,' wire da_fire=dv && dr;',' assign d_nofault=db0 || db1; // This local BRAM interface has no ECC or late bus error.\n wire da_fire=dv && dr;');p.write_text(s)
 p=out/'nc_soc.v';s=p.read_text();s=rep(s,' wire sv,sr,sov,sor,swrite;',' wire dsafe;\n wire sv,sr,sov,sor,swrite;');s=rep(s,'.d_req_valid(dv),','.d_req_nofault(dsafe),.d_req_valid(dv),');s=rep(s,'.dv(dv),','.d_nofault(dsafe),.dv(dv),');p.write_text(s)
 for n in ('nc_core.v','nc_memory.v','nc_local_bus.v','nc_soc.v'):
  for k in g['override_sha256']:
   if Path(k).name==n:g['override_sha256'][k]=sha(out/n)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope='dual_lsu_pair; registered completion forwarding plus explicit primary fault-free RAM grant enables nonalias side store on primary acceptance edge; unknown/MMIO/error-capable targets retain ordered response gating; no early EX request or raw return bypass; not adopted')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED dual_lsu_pair')
if __name__=='__main__':main()
