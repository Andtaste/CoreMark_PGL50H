"""Fast complete only accepted non-failing local stores; drain their response."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 accepted=ROOT/'docs/accepted_dual_baseline.json';d=json.loads(accepted.read_text(encoding='utf-8'));assert d['variant']=='dual_boundary_slots'
 src=ROOT/d['source_directory'];out=src.with_name('load_bp_dual_boundary_storeack');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_core.v';s=p.read_text();s=rep(s,'module nc_core #(parameter ENABLE_BP=1)', 'module nc_core #(parameter ENABLE_BP=1,POST_LOCAL_STORES=0)');s=rep(s,'nc_memory #(.EARLY_REQUEST(1)) memory','nc_memory #(.EARLY_REQUEST(1),.POST_LOCAL_STORES(POST_LOCAL_STORES)) memory');p.write_text(s)
 p=out/'nc_soc.v';s=p.read_text();s=rep(s,' nc_core cpu(',''' // This local bus acknowledges every accepted in-range BRAM write without
 // late errors. Standalone nc_core keeps posted completion disabled.
 nc_core #(.POST_LOCAL_STORES(1)) cpu(''');p.write_text(s)
 p=out/'nc_memory.v';s=p.read_text();s=rep(s,'module nc_memory #(parameter EARLY_REQUEST=0)', 'module nc_memory #(parameter EARLY_REQUEST=0,POST_LOCAL_STORES=0)')
 s=rep(s,' reg slot_valid,sent;', ' reg posted_response;\n reg slot_valid,sent;')
 s=rep(s,'wire response=memory_pending && sent && rsp_valid;', '''// A previous fast-completed local write owns this response, even if a
 // new ALU/load/store has already entered the ordered MEM slot.
 wire response=memory_pending && sent && rsp_valid && !posted_response;''')
 s=rep(s,'wire complete=slot_valid && (!memory_access || response) && (!multiply_access || mul_ready);', '''wire local_write_address=address<32'h00010000 || (address>=32'h10000000 && address<32'h10008000);
 wire store_fast=POST_LOCAL_STORES && memory_pending && kind==5 && local_write_address;
 wire posted_fire=!kill && store_fast && old_request && req_ready;
 wire complete=slot_valid && (!memory_access || response || posted_fire) && (!multiply_access || mul_ready);''')
 s=rep(s,'wire old_request=memory_pending && !sent;', '''// At most one detached response. It may be replaced only as its real
 // response is drained; no assumption of always-ready or one-cycle buses.
 wire response_credit=!posted_response || rsp_valid;
 wire old_request=memory_pending && !sent && response_credit;''')
 s=rep(s,'wire early_request=EARLY_REQUEST && can_accept && valid && input_memory && packet[7:4]==4 && input_local;', 'wire early_request=EARLY_REQUEST && can_accept && valid && input_memory && packet[7:4]==4 && input_local && !old_request && response_credit;')
 s=rep(s,'assign rsp_ready=memory_pending && sent && !kill;', 'assign rsp_ready=posted_response || (memory_pending && sent && !kill);')
 s=rep(s,' always @(posedge clk or negedge rst_n) begin\n  if(!rst_n) begin slot_valid<=0;', ''' // A detached accepted write is architectural and must drain through a
 // younger trap/flush. No store address/data bypass or write buffer added.
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) posted_response<=0;
  else if(posted_fire) posted_response<=1;
  else if(posted_response && rsp_valid) posted_response<=0;
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin slot_valid<=0;''')
 p.write_text(s)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.pop('reused_operand_sha256',None);g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),accepted_dual_sha256=sha(accepted),scope='Local store accepts complete MEM early only under explicit non-failing local-bus contract; one detached response drained separately; standalone default disabled; no early store data/AGU bypass or adoption')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED dual_boundary_storeack')
if __name__=='__main__':main()
