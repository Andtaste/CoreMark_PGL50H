"""Prepare an exact accepted-baseline PDS package before moving the old project."""
from pathlib import Path
from datetime import datetime
import hashlib,json,shutil,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
 descriptor=ROOT/'docs/accepted_dual_baseline.json';a=json.loads(descriptor.read_text(encoding='utf-8'));assert a['variant']=='dual_boundary_next_pairbranch'
 accepted=ROOT/a['source_directory'];base=ROOT/'hardware/pds';stage=ROOT/'hardware/pds_pairbranch_sync_stage';out=ROOT/'docs/pds_main_sync_20261022';backup=ROOT/'hardware/pds_before_pairbranch_20261022'
 assert base.is_dir() and not stage.exists() and not backup.exists() and not out.exists()
 for key in ('source_sha256','ip_sha256','evidence_sha256'):
  for n,h in a[key].items():assert sha(ROOT/n)==h,(key,n)
 g=json.loads((accepted/'generation.json').read_text());pd=json.loads((accepted/'pds/result.json').read_text());assert pd['status']=='PASS'
 # Preserve actual pre-sync state, including any local PLL/build changes.
 old_files=[p for p in sorted(base.rglob('*')) if p.is_file()];old={str(p.relative_to(base)):sha(p) for p in old_files}
 out.mkdir();stage.mkdir();mapping={}
 for d in ('core','perips','sys_bus','top','source'):
  for p in sorted((base/'source'/d).glob('*.v')):
   q=accepted/p.name if str(p.relative_to(ROOT)) in g['override_sha256'] else p
   target=stage/p.relative_to(base);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(q,target)
   mapping[str(target.relative_to(stage))]=dict(accepted_input=str(q.relative_to(ROOT)),sha256=sha(q));assert sha(target)==sha(q)
 shutil.copytree(accepted/'ipcore',stage/'ipcore');shutil.copytree(base/'constraints',stage/'constraints')
 images=stage/'memory';images.mkdir();raw=ROOT/'sw/build/boot.hex';encoded=ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex'
 shutil.copyfile(raw,images/'boot.hex');shutil.copyfile(encoded,images/'boot_interleaved.hex')
 words=[int(s,16) for s in raw.read_text().split()];packed=[int(s,16) for s in encoded.read_text().split()];assert len(words)==16384 and len(packed)==8192
 for i,entry in enumerate(packed):
  b=entry.to_bytes(8,'little');original=bytes(b[j] for j in (0,2,4,6,1,3,5,7));assert original==words[2*i].to_bytes(4,'little')+words[2*i+1].to_bytes(4,'little')
 old_image=encoded.as_posix();new_image=(base/'memory/boot_interleaved.hex').as_posix();rewrites={}
 for p in (stage/'ipcore').rglob('*'):
  if p.is_file() and p.suffix in ('.idf','.v','.vhdl'):
   data=p.read_bytes();new=data.replace(old_image.encode(),new_image.encode())
   if new!=data:p.write_bytes(new);rewrites[str(p.relative_to(stage))]=dict(old_sha256=hashlib.sha256(data).hexdigest(),new_sha256=sha(p),change='INIT_FILE path only; generated primitive INIT parameters unchanged')
 assert rewrites and all('ram1_tdp' in n for n in rewrites)
 for p in (stage/'ipcore').rglob('*.v'):
  assert p.read_bytes().replace(new_image.encode(),old_image.encode())==(accepted/'ipcore'/p.relative_to(stage/'ipcore')).read_bytes(),p
 (images/'README.md').write_text('CoreMark fixed-10 image from the adopted pairbranch baseline.\nboot.hex: 16384 RV32 words. boot_interleaved.hex: vendor A64/B32 initialization encoding, 8192 entries.\nThe RAM1 IP INIT_FILE uses boot_interleaved.hex; do not replace it with raw boot.hex.\nBoth generated INIT parameters and all inverse-decoded words were checked against the accepted baseline.\n',encoding='utf-8')
 # Keep the known PDS structure but invalidate every old flow-stage result.
 text=(base/'new_core.pds').read_text();text=re.sub(r'\(_gci_state \(_integer [0-9]+\)\)', '(_gci_state (_integer 0))',text)
 (stage/'new_core.pds').write_text(text,encoding='utf-8')
 tcl='''# Current adopted pairbranch development baseline. Run in this directory.
set root [file normalize [file dirname [info script]]]
set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484
foreach directory {core perips sys_bus top source} {
 foreach src [lsort [glob -directory "$root/source/$directory" *.v]] {add_design $src}
}
foreach ip {pll ram1_tdp ram2_tdp} {add_design "$root/ipcore/$ip/$ip.idf"}
add_constraint "$root/constraints/board.fdc"
compile -top_module top
synthesize -ads -selected_syn_tool_opt 2
dev_map
pnr -max_ctrl_chain_length 4 -optimize_multi_corner_timing -fix_hold_violation -fix_hold_violation_in_route TRUE
report_timing -max_path 30 -nworst 1
'''
 (stage/'new_core.tcl').write_text(tcl,encoding='utf-8')
 save(out/'before_manifest.json',old);shutil.copyfile(descriptor,out/'accepted_descriptor_snapshot.json');shutil.copyfile(ROOT/'docs/accepted_baseline.json',out/'historical_single_descriptor.json')
 single=json.loads((ROOT/'docs/accepted_baseline.json').read_text(encoding='utf-8'));drift={n:dict(expected=h,actual=sha(ROOT/n) if (ROOT/n).is_file() else None) for n,h in single['source_sha256'].items() if not (ROOT/n).is_file() or sha(ROOT/n)!=h}
 save(out/'prepared.json',dict(status='PREPARED',recorded_at=datetime.now().astimezone().isoformat(),accepted_variant=a['variant'],accepted_descriptor_sha256=sha(descriptor),source_directory=a['source_directory'],primary_project='hardware/pds/new_core.pds',staging_directory=str(stage.relative_to(ROOT)),previous_project_directory=str(backup.relative_to(ROOT)),exact_rtl_mapping=mapping,init_path_rewrites=rewrites,images={str(p.relative_to(stage)):sha(p) for p in images.glob('*.hex')},preexisting_single_descriptor_drift=drift,before_files=len(old),stage_sha256={str(p.relative_to(stage)):sha(p) for p in stage.rglob('*') if p.is_file()},note='Historical immutable descriptors retain their original paths and hashes. Hardware/pds is promoted by explicit user instruction; resolve pre-sync current files under previous_project_directory and before_manifest, not the new active project.'))
 print('PREPARED',len(mapping),'RTL files;',len(old),'old project files protected; all 16384 boot words match')
if __name__=='__main__':main()
