"""Remove an impossible posted-store-to-early-load ready dependency."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/load_bp_dual_boundary_bankreq';out=src.with_name('load_bp_dual_boundary_banklocal');assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text());assert g['accepted_dual_sha256']==sha(ROOT/'docs/accepted_dual_baseline.json')
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v');p=out/'nc_memory.v';s=p.read_text();needle='wire bank_early=EARLY_REQUEST && can_accept && valid && input_memory && packet[7:4]==4 && !old_request && response_credit;';assert s.count(needle)==1;s=s.replace(needle,'''// bank_early requires !old_request, hence posted_fire is impossible.
 // Exclude that impossible completion case before this control fanout.
 wire bank_slot_ok=!slot_valid || ((!memory_access || response) && (!multiply_access || mul_ready) && !exception && !response_error);
 wire bank_early=EARLY_REQUEST && !kill && bank_slot_ok && valid && input_memory && packet[7:4]==4 && !old_request && response_credit;''');p.write_text(s)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']};g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope='Same bank-qualified requests; remove posted_fire/req_ready case which is impossible under !old_request. Control-only equivalent simplification; no extra state/cycle or AGU change; not adopted');(out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED dual_boundary_banklocal')
if __name__=='__main__':main()
