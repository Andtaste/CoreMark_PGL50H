"""Isolated optimization inputs and regression adapter for the current board RTL."""
from pathlib import Path
import argparse, hashlib, json, re, shutil, sys
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'simulation/results/autonomous_20261022'
BOARD=ROOT/'hardware/pds_board5000'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x): p.write_text(json.dumps(x,indent=2)+'\n')
def prepare():
 WORK.mkdir(exist_ok=True)
 snapshot=WORK/'original_board'
 if not snapshot.exists():
  shutil.copytree(BOARD,snapshot)
  save(WORK/'original_manifest.json',{str(p.relative_to(snapshot)):sha(p) for p in snapshot.rglob('*') if p.is_file()})
 for name in ('control','side_select','mem_capture','btb128','btb_fold','branch_equal'):
  dest=WORK/name
  if dest.exists(): continue
  dest.mkdir()
  for folder in ('source','constraints','ipcore','memory'): shutil.copytree(snapshot/folder,dest/folder)
  s=(snapshot/'new_core.pds').read_text()
  s=re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',s)
  (dest/'new_core.pds').write_text(s)
  if name=='side_select':
   p=dest/'source/core/nc_core.v';s=p.read_text()
   old="wire[31:0] side_value=side_branch ? secondary_result[212:181] : side_multiply ? 32'b0 : secondary_result[180:149];"
   new="""// Parallel masks keep the late branch direction out of a second wide mux.
 wire[31:0] side_sequential=ex_side[199:168]+32'd4;
 wire[31:0] side_value=({32{side_branch && side_taken}} & side_target) |
   ({32{side_branch && !side_taken}} & side_sequential) |
   ({32{!side_branch && !side_multiply}} & secondary_result[180:149]);"""
   assert s.count(old)==1;p.write_text(s.replace(old,new))
  if name=='mem_capture':
   p=dest/'source/core/nc_memory.v';s=p.read_text();old='if(start) begin held<=packet;held_side<=side_packet;end'
   assert s.count(old)==1
   s=s.replace(old,'// Free or completing slots may sample payload; slot_valid still owns it.\n  if(!slot_valid || complete) begin held<=packet;held_side<=side_packet;end')
   p.write_text(s)
  if name=='btb128':
   p=dest/'source/core/nc_btb.v';s=p.read_text()
   s=s.replace('reg[31:0] valid;','reg[63:0] valid;').replace('reg[23:0] tags','reg[22:0] tags').replace('[0:31]','[0:63]')
   s=s.replace('wire[4:0] r=lookup_pc[7:3],w=update_pc[7:3];','wire[5:0] r=lookup_pc[8:3],w=update_pc[8:3];').replace('lookup_pc[31:8]','lookup_pc[31:9]').replace('update_pc[31:8]','update_pc[31:9]')
   s=s.replace('same 64-entry BTB: 32 entries, full PC[31:8] tag','128-entry BTB: 64 entries, full PC[31:9] tag')
   p.write_text(s)
  if name=='btb_fold':
   p=dest/'source/core/nc_btb.v';s=p.read_text()
   old='wire[4:0] r=lookup_pc[7:3],w=update_pc[7:3];'
   assert s.count(old)==1
   p.write_text(s.replace(old,'wire[4:0] r=lookup_pc[7:3]^lookup_pc[12:8],w=update_pc[7:3]^update_pc[12:8];'))
  if name=='branch_equal':
   p=dest/'source/core/nc_execute.v';s=p.read_text()
   s=s.replace(' wire is_md=', ''' // Preserve short parallel equality groups instead of a full-word carry chain.
 wire[3:0] branch_equal_groups /* synthesis syn_keep=1 */;
 assign branch_equal_groups={a[31:24]==b[31:24],a[23:16]==b[23:16],a[15:8]==b[15:8],a[7:0]==b[7:0]};
 wire is_md=''')
   s=s.replace('0:taken=a==b;1:taken=a!=b;', '0:taken=&branch_equal_groups;1:taken=!(&branch_equal_groups);')
   p.write_text(s)
  save(dest/'inputs.json',{str(p.relative_to(dest)):sha(p) for p in dest.rglob('*') if p.is_file()})
def simulate(name,phase):
 sys.path.insert(0,str(ROOT/'tools'))
 import research_dual_issue as trial
 dest=WORK/name
 # Keep the original regression assertions and independent ISA model. Rebind
 # its obsolete single-issue provenance to immutable current-board inputs.
 manifest=WORK/'current_baseline.json'
 save(manifest,{'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in (WORK/'original_board/source').rglob('*.v')}})
 flat=ROOT/('simulation/results/load_bp_dual_boundary_auto_'+name)
 flat.mkdir(exist_ok=True)
 overrides={}
 for p in (dest/'source').rglob('*.v'):
  if p.name in ('top.v','nc_uart.v'):continue
  shutil.copyfile(p,flat/p.name)
  key=str(Path('hardware/pds/source')/p.relative_to(dest/'source'))
  overrides[key]=sha(p)
 model=ROOT/'simulation/results/load_bp_dual_boundary_next_pairbranch/pango_ram_wide_models.v'
 shutil.copyfile(model,flat/model.name)
 save(flat/'generation.json',dict(override_sha256=overrides,baseline_sha256=sha(manifest),ip_sha256={}))
 code=(ROOT/'tools/research_dual_issue.py').read_text().replace("ROOT/'docs/accepted_baseline.json'","ROOT/'simulation/results/autonomous_20261022/current_baseline.json'")
 # main needs the module globals so wrappers can supply their instrumentation.
 exec(compile(code,str(ROOT/'tools/research_dual_issue.py'),'exec'),trial.__dict__)
 from run_dual_next_trial import main
 sys.argv=['run_dual_next_trial.py','--variant','dual_boundary_auto_'+name,'--phase',phase]
 main()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','simulate']);p.add_argument('--name',default='control');p.add_argument('--phase',default='checks');a=p.parse_args()
 if a.action=='prepare':prepare()
 else:simulate(a.name,a.phase)
