"""Verify and freeze latency-boundary experiments without changing adoption."""
from pathlib import Path
import hashlib,json,re,shutil,zipfile
from parse_dual_joint_timing import paths
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'docs/dual_boundary';NAMES=['dual_boundary_'+s for s in ('slot','early','read','launch')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def main():
 assert not (DEST/'manifest.json').exists();DEST.mkdir(exist_ok=True)
 def verify(x,label):
  for key in ('input_sha256','actual_compile_sha256','ip_sha256'):
   for n,h in x.get(key,{}).items():
    p=ROOT/n
    if not p.exists() and n.replace('\\','/').startswith('tmp/'):p=ROOT.parent/n
    assert p.is_file() and sha(p)==h,(label,n,h,sha(p) if p.is_file() else None)
    if not n.replace('\\','/').startswith('simulation/results/load_bp_dual_boundary_') and not n.replace('\\','/').startswith('simulation/results/dual_boundary_common_final') and p.suffix!='.adf':copy(p,DEST/'inputs'/n)
 accepted=read(ROOT/'docs/accepted_dual_baseline.json');assert sha(ROOT/'docs/accepted_dual_baseline.json')=='acc8a0f8be1dc90d67e6cda8d18fc000911cc4b25a8021ab0f7b17ec244abb01'
 for k in ('source_sha256','ip_sha256','evidence_sha256'):
  for n,h in accepted[k].items():assert sha(ROOT/n)==h,(k,n)
 assert sha(ROOT/'docs/accepted_baseline.json')==accepted['single_issue_reference_sha256'];assert sha(ROOT/'hardware/pds/report_timing/top.rtr')==accepted['single_issue_sta_sha256']
 prior={}
 for n in ('dual_fwd','dual_fan','dual_admit','dual_native','dual_types','dual_joint','dual_split','dual_legacy','dual_lsu'):
  m=read(ROOT/'docs'/n/'manifest.json')
  for p,h in m.items():assert sha(ROOT/'docs'/n/p)==h,(n,p)
  prior[n]=len(m)
 rows={};snapshots={}
 for name in NAMES:
  src=ROOT/('simulation/results/load_bp_'+name);g=read(src/'generation.json');verify(g,name+'/generation');assert g['accepted_dual_sha256']==sha(ROOT/'docs/accepted_dual_baseline.json')
  for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
  gen='generate_dual_boundary'+('_read' if name.endswith('_read') else '_launch' if name.endswith('_launch') else '')+'.py';assert sha(ROOT/'tools'/gen)==g['generator_sha256']
  checks={}
  subs=[('checks',63),('dual_checks',7),('pair_checks',6),('cancel_checks',4),('audit_checks',4),('timeline_checks',4),('memory_checks',4),('operands_checks',1)]
  if name in NAMES[2:]:subs +=[('protocol',8),('mul_protocol',4)]
  if name.endswith('_launch'):subs +=[('address_contract',10)]
  for sub,count in subs:
   x=read(src/sub/'result.json');verify(x,name+'/'+sub);assert x['status']=='PASS' and len(x['tests'])==count,(name,sub);checks[sub]=count
  for phase in ('performance','validation'):
   x=read(src/phase/'result.json');verify(x,name+'/'+phase);assert x['status']=='PASS' and x['override_sha256']==g['override_sha256'];ref=read(ROOT/f'simulation/results/load_bp_dual_fwd_share/{phase}/result.json')
   for k in ('Retired instructions','Retired loads','Retired stores','BJP instructions','seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal'):assert x['metrics'][k]==ref['metrics'][k],(name,phase,k)
  sim=read(src/'performance/result.json');pd=read(src/'pds/result.json');verify(pd,name+'/pds');assert sha(src/'pds/run.tcl')==pd['tcl_sha256'];assert pd.get('pds_exit_code')==0 or pd.get('sta_exit_code')==0
  queries={}
  if name!='dual_boundary_slot':
   q=read(src/'boundary_paths/result.json');verify(q,name+'/paths')
   for n,h in q['report_sha256'].items():assert sha(src/'boundary_paths'/n)==h
   queries=q['paths']
  ram={}
  for inst,kind in re.findall(r'^([^;\r\n]+);(gopRAM\w+)',(src/'pds/place_route/top_pnr.netlist').read_text(errors='replace'),re.M):
   cat='instruction_fifo' if '/fetch/even_inst' in inst or '/fetch/odd_inst' in inst else 'btb' if '/predictor.' in inst else 'regfile' if '/rf/' in inst else 'exmem_fifo' if '/memory_queue/' in inst else inst;ram[cat]=ram.get(cat,0)+1
  assert sum(ram.values())==pd['resources']['Distributed RAM']
  cycles=int(sim['metrics']['Stats window cycles']);retired=int(sim['metrics']['Retired instructions']);side=sim['dual']['secondary_retired'];rows[name]=dict(status='FUNCTIONAL_PASS_NOT_ADOPTED',cycles=cycles,ipc=retired/cycles,timing_status=pd['status'],estimated_fmax_mhz=pd['estimated_fmax_mhz'],resources=pd['resources'],corners=pd['corners'],ram_breakdown=ram,occupancy=dict(primary_percent=(retired-side)/cycles*100,secondary_percent=side/cycles*100),same_clock_gain_vs_accepted_percent=(accepted['coremark_stats_cycles']/cycles-1)*100,metrics=sim['metrics'],dual=sim['dual'],boundary=sim['boundary'],multiply=sim['multiply'],predictor=sim['predictor'],timeline=read(src/'timeline_checks/result.json')['tests'],checks=checks,global_paths=paths(src/'pds/report_timing/top.rtr'),boundary_paths=queries,flow_note=pd.get('scope'))
  for p in src.rglob('*'):
   if not p.is_file():continue
   rel=p.relative_to(src)
   if 'obj' in rel.parts or p.suffix in ('.vvp','.elf','.bin','.o','.exe','.pyc'):continue
   if rel.parts[0]=='pds' and rel.as_posix() not in ('pds/result.json','pds/run.tcl','pds/build.log','pds/report_timing/top.rtr','pds/device_map/top.dmr','pds/place_route/top.prr','pds/synthesize/apm_drm_lutram_utilization.log'):continue
   copy(p,DEST/name/rel)
 common=ROOT/'simulation/results/dual_boundary_common_final';summary=read(common/'comparison.json');verify(summary,'common comparison')
 for target in ('old','read','fifo'):
  x=read(common/target/'result.json');verify(x,'common/'+target);assert x['status']=='PASS'
 for p in common.rglob('*'):
  if p.is_file() and 'obj' not in p.relative_to(common).parts and p.suffix not in ('.vvp','.o','.exe'):copy(p,DEST/'common'/p.relative_to(common))
 # Earlier unsupported adapters and the read-payload preflight remain diagnostics.
 for folder in ('dual_boundary_common','dual_boundary_common_v4','dual_boundary_suite','load_bp_dual_boundary_load'):
  base=ROOT/'simulation/results'/folder
  for p in base.rglob('*'):
   if p.is_file() and p.suffix=='.log' and 'obj' not in p.parts:copy(p,DEST/'diagnostics'/folder/p.relative_to(base))
 repro=ROOT/'simulation/results/dual_boundary_repro/reproduction_result.json';x=read(repro);assert x['status']=='PASS' and x['override_sha256']==read(ROOT/'simulation/results/load_bp_dual_boundary_launch/generation.json')['override_sha256'];copy(repro,DEST/'reproduction_result.json')
 with zipfile.ZipFile(DEST/'routed_snapshots.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
  for n in NAMES:
   for file in ('top_pnr.adf','top_pnr.netlist'):
    p=ROOT/f'simulation/results/load_bp_{n}/pds/place_route/{file}';key=n+'/'+file;z.write(p,key);snapshots[key]=sha(p)
 with zipfile.ZipFile(DEST/'routed_snapshots.zip') as z:
  for n,h in snapshots.items():assert hashlib.sha256(z.read(n)).hexdigest()==h
 save(DEST/'routed_content_sha256.json',snapshots)
 for p in (ROOT/'tools').glob('*dual_boundary*.py'):copy(p,DEST/'tools'/p.name)
 for n in ('research_dual_issue.py','run_dual_legacy.py','profile_dual_joint.py','check_dual_joint_cancel.py','check_dual_joint_pairs.py','check_dual_joint_reg_protocol.py','check_dual_joint_reg_mul_protocol.py','check_dual_legacy.py','check_dual_native_extra.py','report_dual_lsu_ram_paths.py','parse_dual_joint_timing.py','research_dual_ram_pds.py'):copy(ROOT/'tools'/n,DEST/'tools'/n)
 copy(ROOT/'docs/accepted_dual_baseline.json',DEST/'accepted_dual_baseline.json');copy(ROOT.parent/'tmp/dual_round50_20261019/after/source_hashes.json',DEST/'old_source_hashes.json')
 cleanup=ROOT/'simulation/cleanup_dual_boundary_result.json';copy(cleanup,DEST/'cleanup.json')
 save(DEST/'comparison.json',dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',accepted_variant_unchanged=accepted['variant'],prior_archives_verified=prior,candidates=rows,common=summary,limits=[
 'Fixed 1/10 diagnostic images, same original new-core hashes between candidate PDS trials; PLL 75MHz unchanged, no board/Flash/game test.',
 'Common old/new CPU comparison patches exactly four CSR reads 7cb..7ce after stats stop to zero on all targets; the measured retired PC hash/count remains identical to the unpatched new-core images. CPU IF formatting and old atomic memory acceptance require adapters. Common behavioral service is not original SoC or a physically implemented A64 cross-line fetch.',
 'Slot PNR completed in the original 900s run, but the flow timed out during STA database loading. Read-only recovery completed STA on the identical routed ADF without rerouting.',
 'No raw load-response-to-EX path or L1 duplicate broadcast. New MEM completion -> spill FIFO write/selection control exists; EX input credit remains registered occupancy. Early EX request/data/address paths are explicitly measured, not declared universally short.',
 'The failed load-only preflight changed ignored read payload during ownership transfer under backpressure. Full-core protocol tests rejected it before PNR. Read/launch fix ignored read data/mask to constants; CRC alone was not treated as correctness proof.',
 'Initial observer adaptations: MUL classification now uses held slot rather than input, and timeline allows spill queue delay. Old report firmware rejects IPC>1 when printing; report computes IPC from independently checked hardware counters.'
 ]))
 print('Verified and copied boundary archive')
def finish():
 copy(ROOT/'docs/dual_boundary.md',DEST/'report.md');save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
if __name__=='__main__':main()
