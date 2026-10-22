"""Verify and freeze pairing census, sliding-window trials, and routed evidence."""
from pathlib import Path
import hashlib,json,shutil,zipfile,re
from archive_dual_issue import paths
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'docs/dual_types'
SUFFIXES=('branch','mul','both','compact','slide','bound','slide_bound','admit','slide_admit')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def verify(x):
 for key in ('input_sha256','actual_compile_sha256','ip_sha256'):
  for n,h in x.get(key,{}).items():
   p=ROOT/n;assert sha(p)==h,(key,n)
   if p.suffix!='.adf' and not n.replace('\\','/').startswith(('simulation/results/load_bp_dual_types','simulation/results/load_bp_dual_type_control','simulation/results/dual_type_census')):copy(p,DEST/'inputs'/n)
def preserve(src,dest):
 for p in src.rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(src)
  if 'obj' in rel.parts or p.suffix in ('.vvp','.elf','.bin','.o','.exe','.pyc'):continue
  if rel.parts[0]=='pds' and rel.as_posix() not in ('pds/result.json','pds/run.tcl','pds/build.log','pds/report_timing/top.rtr','pds/device_map/top.dmr','pds/place_route/top.prr','pds/synthesize/apm_drm_lutram_utilization.log'):continue
  copy(p,dest/rel)
def ram_counts(netlist):
 d={}
 for name,kind in re.findall(r'^([^;\r\n]+);(gopRAM\w+)',netlist.read_text(errors='replace'),re.M):
  cat='instruction_fifo' if '/fetch/instructions' in name else 'btb' if '/predictor.' in name else 'regfile' if '/rf/' in name else 'exmem_fifo' if '/memory_queue/' in name else 'adjacency_links' if '/fetch/links' in name else name
  d[cat]=d.get(cat,0)+1
 return d
def main():
 DEST.mkdir(exist_ok=True);accepted=read(ROOT/'docs/accepted_dual_baseline.json');assert accepted['variant']=='dual_fwd_share'
 for key in ('source_sha256','evidence_sha256','ip_sha256'):
  for n,h in accepted[key].items():assert sha(ROOT/n)==h,(key,n)
 assert sha(ROOT/'docs/accepted_baseline.json')==accepted['single_issue_reference_sha256']
 assert sha(ROOT/'hardware/pds/report_timing/top.rtr')==accepted['single_issue_sta_sha256']
 for n,h in read(ROOT/'docs/accepted_baseline.json')['source_sha256'].items():assert sha(ROOT/n)==h,n
 prior={}
 for name in ('dual_fwd','dual_fan','dual_admit','dual_native'):
  m=read(ROOT/'docs'/name/'manifest.json')
  for n,h in m.items():assert sha(ROOT/'docs'/name/n)==h,(name,n)
  prior[name]=len(m)
 copy(ROOT/'docs/dual_native_decision.json',DEST/'previous_round_rejected.json')
 parent=ROOT/'simulation/results/load_bp_dual_fwd_share';base=read(parent/'performance/result.json');bpds=read(parent/'pds/result.json')
 control=ROOT/'simulation/results/load_bp_dual_type_control';profile=read(control/'performance/result.json');verify(profile)
 for k in ('metrics','dual','predictor','multiply'):assert profile[k]==base[k],k
 assert sum(v['count'] for v in profile['type_profile'])==583920
 assert sum(profile['front_origin'][k] for k in ('unexpected','upper_entry','predicted_taken','leftover','other_single'))==1397635
 preserve(control,DEST/'profile_control')
 results={}
 for suffix in SUFFIXES:
  name='dual_types_'+suffix;src=ROOT/('simulation/results/load_bp_'+name);g=read(src/'generation.json');verify(g)
  for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
  assert sha(src/'nc_operands.v')==sha(parent/'nc_operands.v')
  gen='generate_dual_types.py' if suffix in ('branch','mul','both') else 'generate_dual_slide.py' if suffix in ('compact','slide') else 'generate_dual_type_bound.py' if 'bound' in suffix else 'generate_dual_type_admit.py'
  assert sha(ROOT/'tools'/gen)==g['generator_sha256'],gen
  for p in (src/'ipcore').rglob('*'):
   if p.is_file() and p.suffix in ('.v','.idf'):assert sha(p)==sha(parent/'ipcore'/p.relative_to(src/'ipcore')),p
  for sub,count in (('checks',63),('dual_checks',7),('pair_checks',6)):
   q=read(src/sub/'result.json');assert q['status']=='PASS' and len(q['tests'])==count,(name,sub);verify(q)
  q=read(src/'audit/result.json');assert q['status']=='PASS' and len(q['tests'])>=6;verify(q)
  for phase in ('performance','validation'):
   q=read(src/phase/'result.json');assert q['status']=='PASS';verify(q);assert q['override_sha256']==g['override_sha256']
   ref=read(parent/phase/'result.json')
   for k in ('Retired instructions','Retired loads','Retired stores','BJP instructions','seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal'):assert q['metrics'][k]==ref['metrics'][k],(name,k)
   assert q['predictor']['resolved']==ref['predictor']['resolved']
  sim=read(src/'result.json');pds=read(src/'pds/result.json');assert pds['status'] in ('PASS','TIMING_FAILED') and pds['pds_exit_code']==0;verify(sim);verify(pds)
  assert sha(src/'pds/run.tcl')==pds['tcl_sha256']
  preserve(src,DEST/name);slow=paths(src/'pds/report_timing/top.rtr');save(DEST/name/'slow_setup_paths.json',slow)
  prefix='dual_type_finish_paths' if suffix in ('bound','slide_bound','admit','slide_admit') else 'dual_types_paths'
  target=ROOT/'simulation/results'/prefix/name;q=read(target/'result.json');verify(q)
  for n,h in q['report_sha256'].items():assert sha(target/n)==h,n
  preserve(target,DEST/'targeted_paths'/name)
  cycles=int(sim['metrics']['Stats window cycles']);gain=int(base['metrics']['Stats window cycles'])/cycles;ram=ram_counts(src/'pds/place_route/top_pnr.netlist');assert sum(ram.values())==pds['resources']['Distributed RAM'],(name,ram)
  results[name]=dict(cycles=cycles,ipc=int(sim['metrics']['Retired instructions'])/cycles,same_clock_gain_percent=(gain-1)*100,estimated_fmax_mhz=pds['estimated_fmax_mhz'],timing_status=pds['status'],resources=pds['resources'],ram_breakdown=ram,corners=pds['corners'],estimated_peak_gain_percent=(gain*pds['estimated_fmax_mhz']/bpds['estimated_fmax_mhz']-1)*100,break_even_fmax_mhz=bpds['estimated_fmax_mhz']/gain,dual=sim['dual'],multiply=sim['multiply'],predictor=sim['predictor'],slow_setup_paths=slow,targeted_paths=q['paths'])
 for suffix in ('compact','bound','admit'):
  for phase in ('performance','validation'):
   x=read(ROOT/f'simulation/results/load_bp_dual_types_{suffix}/{phase}/result.json');y=read(ROOT/f'simulation/results/load_bp_dual_types_both/{phase}/result.json')
   for k in ('metrics','dual','predictor','multiply'):assert x[k]==y[k],(suffix,phase,k)
 for suffix in ('slide_bound','slide_admit'):
  for phase in ('performance','validation'):
   x=read(ROOT/f'simulation/results/load_bp_dual_types_{suffix}/{phase}/result.json');y=read(ROOT/f'simulation/results/load_bp_dual_types_slide/{phase}/result.json')
   for k in ('metrics','dual','predictor','multiply'):assert x[k]==y[k],(suffix,phase,k)
 census={}
 for suffix in ('branch','mul','bound','slide_bound'):
  src=ROOT/f'simulation/results/dual_type_census/dual_types_{suffix}';q=read(src/'census.json');assert q['status']=='PASS' and q['parent_profile_identical'];verify(q);preserve(src,DEST/'census'/suffix);census[suffix]=q['census']
 snapshots={}
 with zipfile.ZipFile(DEST/'routed_snapshots.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
  for suffix in SUFFIXES:
   name='dual_types_'+suffix
   for f in ('top_pnr.adf','top_pnr.netlist'):
    p=ROOT/('simulation/results/load_bp_'+name+'/pds/place_route/'+f);n=name+'/'+f;z.write(p,n);snapshots[n]=sha(p)
 with zipfile.ZipFile(DEST/'routed_snapshots.zip') as z:
  for n,h in snapshots.items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 save(DEST/'routed_content_sha256.json',snapshots)
 for pattern in ('*dual_type*.py','*dual_slide*.py'):
  for p in (ROOT/'tools').glob(pattern):copy(p,DEST/'tools'/p.name)
 for n in ('research_dual_issue.py','research_dual_ram_pds.py','archive_dual_issue.py','profile_dual_admit.py'):copy(ROOT/'tools'/n,DEST/'tools'/n)
 copy(ROOT/'docs/accepted_dual_baseline.json',DEST/'accepted_dual_baseline.json')
 eligible=[(x['estimated_peak_gain_percent'],n) for n,x in results.items() if x['timing_status']=='PASS' and x['estimated_peak_gain_percent']>0];preferred=max(eligible)[1] if eligible else 'dual_fwd_share'
 save(DEST/'comparison.json',dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',preferred_research_candidate=preferred,accepted_dual_unchanged=True,baseline_pds=bpds,type_profile=profile['type_profile'],front_origin=profile['front_origin'],census=census,candidates=results,prior_archive_verified_files=prior,limits=[
  'One physical run per immutable RTL variant; same PDS options/constraints/PLL/images, no seed sweep.',
  'Counters count issued speculative groups, not mutually exclusive root causes: RAW/WAW/older/resource/prediction columns can overlap. clean_plain allows predicted conditional branches, requires ordinary ALU primary, and is not a cycle-saving prediction.',
  'Front provenance categories and offline cross opportunities are authoritative only in the byte-identical profiling control. Candidate bench provenance logic was not adapted to cross-window head advancement; do not compare candidate front_origin fields.',
  'Census repeated byte-identical RTL/image with bench-only counters and verified entire performance/predictor/multiply/dual profiles identical. Census for equivalent compact/admission variants is inherited after both image profiles match.',
  'Conditional branch only, aligned target; no JAL/JALR side, no LSU side. Extended pairs require legal ordinary ALU primary and no source/WAW dependency; no four-operand waiting queue.',
  'Two ALUs, one shared original multiplier pipeline and one LSU. Secondary divider disabled. Original tagged operand queue and EX/MEM width249/depth4 unchanged.',
  'SAT checks local legal-instruction decode identities and admission invariants, not whole-core sequential equivalence. Differential traces and targeted precise exceptions cover runtime behavior.',
  'Initial core smoke monitor name collision was repaired in a new monitor/wrapper before passing checks; initial diagnostic retained. A generic slide microtest had only two side not-taken branches because pairing shifted; a new directed sliding test covers 64 taken/64 not-taken and 63 double-group pops per run. No passing RTL was edited in place.',
  'Expanded type predecode and branch/MUL results make some formerly constant EX/MEM bits variable; final mapped RAM counts come from routed netlist and match device-map resources. Sliding cache adds a second instruction RAM read copy and two adjacency RAM primitives.',
  'Fmax is estimated; CoreMark is a short diagnostic. PLL remains ~75MHz; no board/Flash/game validation.'
 ]))
 print(json.dumps({n:{k:v for k,v in x.items() if k in ('cycles','ipc','estimated_fmax_mhz','estimated_peak_gain_percent','resources','timing_status')} for n,x in results.items()},indent=2))
def finish_manifest():
 copy(ROOT/'docs/dual_types.md',DEST/'report.md');save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
if __name__=='__main__':main();finish_manifest()
