"""Verify and preserve the isolated RAM/logic trials without promotion."""
from pathlib import Path
import hashlib,json,shutil
from archive_dual_issue import paths

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'docs/dual_ram'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def copy(a,b):b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a,b)

def verify(record):
 for key in ('input_sha256','actual_compile_sha256','ip_sha256','external_library_sha256'):
  for n,h in record.get(key,{}).items():
   p=Path(n) if Path(n).is_absolute() else ROOT/n
   assert p.is_file() and sha(p)==h,(key,n,h)
   if key!='external_library_sha256' and not str(p.relative_to(ROOT)).replace('\\','/').startswith('simulation/results/load_bp_dual_ram'):
    copy(p,DEST/'inputs'/p.relative_to(ROOT))

def main():
 DEST.mkdir(exist_ok=True)
 accepted=ROOT/'docs/accepted_baseline.json';base=read(accepted)
 assert sha(accepted)=='f9266e85c40bf5a5feaa9d54f1ec77389d00a2feb02b4ed74573b5b1bc171d86'
 for n,h in base['source_sha256'].items():assert sha(ROOT/n)==h,n
 sta=ROOT/'hardware/pds/report_timing/top.rtr'
 assert sha(sta)=='047c7504f1f3967d2499de007e44faa87013cebec03c94b941682521c12794d9'
 prior=read(ROOT/'simulation/results/load_bp_dual_issue_predecode/result.json')
 prior_pds=read(ROOT/'simulation/results/load_bp_dual_issue_predecode/pds/result.json')
 results={}
 for name in ('dual_ram','dual_ram_wide','dual_ram_logic','dual_ram_alu'):
  src=ROOT/('simulation/results/load_bp_'+name);g=read(src/'generation.json');sim=read(src/'result.json');pds=read(src/'pds/result.json')
  for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h,n
  for n,h in g.get('ip_sha256',{}).items():assert sha(ROOT/n)==h,n
  for p in src.rglob('result.json'):
   if len(p.relative_to(src).parts)>2:continue
   x=read(p);verify(x)
   assert x['status']=='PASS' or (name=='dual_ram_wide' and p.parent.name=='hardware_init_check'),p
  for key in ('metrics','predictor','multiply','dual'):assert sim[key]==prior[key],(name,key)
  if name in ('dual_ram_logic','dual_ram_alu'):
   for sub,count in (('checks',63),('dual_checks',5),('equivalence',5),('audit',5)):
    assert len(read(src/sub/'result.json')['tests'])==count,(name,sub)
   val=read(src/'validation/result.json')
   for key in ('metrics','predictor','multiply','dual'):
    assert val[key]==read(ROOT/'simulation/results/load_bp_dual_issue_predecode/validation/result.json')[key],(name,'validation',key)
  # Preserve text sources, generated IP, original tests and reports. Do not
  # redistribute the external Pango primitive or generated simulator binaries.
  for p in src.rglob('*'):
   if not p.is_file() or 'obj' in p.relative_to(src).parts:continue
   rel=p.relative_to(src)
   if rel.parts[0]=='pds':
    if rel.as_posix() not in ('pds/result.json','pds/run.tcl','pds/build.log','pds/report_timing/top.rtr','pds/device_map/top.dmr','pds/synthesize/apm_drm_lutram_utilization.log'):continue
   elif p.suffix.lower() in ('.vvp','.elf','.bin','.o','.exe','.pyc'):continue
   copy(p,DEST/name/rel)
  timing=paths(src/'pds/report_timing/top.rtr');save(DEST/name/'slow_setup_paths.json',timing)
  cycles=int(sim['metrics']['Stats window cycles']);gain=base['coremark_stats_cycles']/cycles
  results[name]=dict(qualification='INVALIDATED_VENDOR_INITIALIZATION' if name=='dual_ram_wide' else ('PILOT_LIMITED_CHECKS' if name=='dual_ram' else 'QUALIFIED_RESEARCH'),
   cycles=cycles,retired=int(sim['metrics']['Retired instructions']),ipc=int(sim['metrics']['Retired instructions'])/cycles,
   estimated_fmax_mhz=pds['estimated_fmax_mhz'],resources=pds['resources'],corners=pds['corners'],
   delta_vs_previous_dual={k:v-prior_pds['resources'][k] for k,v in pds['resources'].items()},
   estimated_peak_gain_vs_accepted_percent=(gain*pds['estimated_fmax_mhz']/base['estimated_fmax_mhz']-1)*100,
   slow_setup_paths=timing)
 oldroot=ROOT.parent/'CoreMark_PGL50H-2';oldpath=oldroot/'simulation/results/reports/dual_round50/evidence/report.json';old=read(oldpath)
 sourceproof={}
 for n in ('ifu.v','tinyriscv_core.v','gpr_reg.v','idu.v'):
  rel='hardware/pds/source/core/'+n;p=oldroot/rel
  expected=old['source_sha256'].get(rel,old['production_before_hashes'].get(rel))
  assert expected is not None and sha(p)==expected,rel
  sourceproof[rel]=sha(p);copy(p,DEST/'old_comparison'/n)
 copy(oldpath,DEST/'old_comparison/round50_report.json')
 save(DEST/'old_comparison/provenance.json',dict(report_sha256=sha(oldpath),current_source_matches_report=sourceproof,
  old_status=old['status'],limits='Different firmware/build and iteration count; descriptive comparison, not a same-image A/B. Use window secondary_retired=78480, not whole-simulation 113212.'))
 for folder in ('tools','simulation/research/dual_ram'):
  files=(ROOT/folder).glob('*dual_ram*.py') if folder=='tools' else (ROOT/folder).iterdir()
  for p in files:
   if p.is_file():copy(p,DEST/'reproduction'/p.relative_to(ROOT))
 for n in ('generate_dual_issue.py','generate_dual_predecode.py','research_dual_issue.py','check_dual_alu_decode.py','generate_dual_ram_alu.py','run_dual_ram_alu.py','archive_dual_issue.py'):
  copy(ROOT/'tools'/n,DEST/'reproduction/tools'/n)
 for n in ('accepted_baseline.json','dual_ram.md'):copy(ROOT/'docs'/n,DEST/n)
 # Verify the previous archive rather than modifying its accepted evidence.
 manifest=read(ROOT/'docs/dual_issue/manifest.json')
 for n,h in manifest.items():assert sha(ROOT/'docs/dual_issue'/n)==h,n
 result=dict(status='RESEARCH_COMPLETE_NOT_ADOPTED',production_unchanged=True,user_accepted=False,
  preferred_research_candidate='dual_ram_logic',previous_dual=prior_pds,candidates=results,
  simplified_secondary_decode='dual_ram_alu is equivalent but saves only 11 LUT / 2 FF and loses 1.206 MHz versus dual_ram_logic; not preferred.',
  accepted_sha256=sha(accepted),production_sta_sha256=sha(sta),previous_archive_verified_files=len(manifest),
  limits=['All qualified runs use identical fixed images and have identical cycles/predictor/multiply/dual metrics.',
   'One PDS run per candidate; unchanged production PLL, constraints, options; Fmax is an estimate, no board test.',
   'No EX direct RAM bypass; registered queue credit remains; existing MEM queue to RAM enable fanout remains a bottleneck.',
   'Generated asymmetric IP initialization was verified against the actual vendor primitive; external primitive is hashed, not copied.'])
 save(DEST/'comparison.json',result)
 save(DEST/'manifest.json',{str(p.relative_to(DEST)):sha(p) for p in sorted(DEST.rglob('*')) if p.is_file() and p.name!='manifest.json'})
 print(json.dumps({k:{n:v for n,v in x.items() if n in ('qualification','estimated_fmax_mhz','resources','estimated_peak_gain_vs_accepted_percent')} for k,x in results.items()},indent=2))

if __name__=='__main__':main()
