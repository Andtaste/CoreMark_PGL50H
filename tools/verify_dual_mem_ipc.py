"""Verify baseline observation, cycle-equivalent MMIO change and exact reuse."""
from pathlib import Path
import hashlib,json,argparse,contextlib,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=('evidence','reproduce'),required=True);a=ap.parse_args();out=ROOT/'simulation/results/dual_mem_ipc_verify';out.mkdir(exist_ok=True);inputs=[Path(__file__).resolve()];tests=[]
 accepted=ROOT/'docs/accepted_dual_baseline.json';d=read(accepted);assert d['variant']=='dual_boundary_slots';ref=ROOT/d['source_directory'];probe=ref.with_name('load_bp_dual_boundary_memprobe');first=ref.with_name('load_bp_dual_boundary_storeack');final=ref.with_name('load_bp_dual_boundary_storemmio')
 if a.mode=='evidence':
  for key,h in read(probe/'generation.json')['override_sha256'].items():assert sha(ref/Path(key).name)==h
  r=read(ref/'performance/result.json');p=read(probe/'performance/result.json')
  for key in ('metrics','predictor','multiply','dual','joint','boundary'):assert r[key]==p[key],key
  inputs +=[accepted,ref/'performance/result.json',probe/'performance/result.json'];tests +=['PASS observation RTL exact accepted hash and all baseline metrics/profiles unchanged']
  for phase in ('performance','validation'):
   f=read(first/phase/'result.json');z=read(final/phase/'result.json');assert f['status']==z['status']=='PASS'
   for key in ('metrics','predictor','multiply','dual','joint','boundary','mem_ipc','load_queue','store_followers'):assert f[key]==z[key],(phase,key)
   inputs +=[first/phase/'result.json',final/phase/'result.json'];tests +=['PASS '+phase+' all statistics unchanged by registered MMIO decode']
  for name in ('nc_operands.v','nc_regfile.v','nc_fetch.v','nc_mul_pipeline.v','nc_execute.v','nc_btb.v','nc_csr.v','nc_stats.v'):
   assert sha(ref/name)==sha(first/name)==sha(final/name);inputs +=[ref/name,first/name,final/name]
  ev=ref/'operand_checks/result.json';assert read(ev)['status']=='PASS' and read(ev)['cycles']==300000;inputs.append(ev);tests +=['PASS exact accepted operand source reuses 300000-cycle independent equivalence; changed W schedule separately checked by real-SoC tag monitors']
  for name in ('nc_core.v','nc_memory.v','nc_soc.v'):
   assert sha(first/name)==sha(final/name);inputs +=[first/name,final/name]
  for sub in ('posted_module','memory_checks','address_contract','protocol','mul_protocol','dual_checks'):
   ev=first/sub/'result.json';assert read(ev)['status']=='PASS';inputs.append(ev)
  tests +=['PASS identical core/MEM module reuses first-trial standalone response tests and core tags; final SoC separately regressed']
 else:
  dest=ROOT/'simulation/results/dual_mem_ipc_repro';dest.mkdir(exist_ok=False)
  for name,toolname,pattern in (
   ('memprobe','generate_dual_mem_ipc.py',"out=src.with_name('load_bp_'+a.variant)"),
   ('storeack','generate_dual_store_ack.py',"out=src.with_name('load_bp_dual_boundary_storeack')"),
   ('storemmio','generate_dual_store_ack_mmio.py',"out=src.with_name('load_bp_dual_boundary_storemmio')")):
   src=ROOT/('simulation/results/load_bp_dual_boundary_'+name);target=dest/name;tool=ROOT/'tools'/toolname;s=tool.read_text();assert s.count(pattern)==1;s=s.replace(pattern,'out=Path('+repr(str(target))+')');ns={'__file__':str(tool),'__name__':'mem_repro'};exec(compile(s,str(tool),'exec'),ns);sys.argv=[str(tool)]
   with (out/(name+'_reproduction.log')).open('w') as log,contextlib.redirect_stdout(log):ns['main']()
   assert read(src/'generation.json')['override_sha256']==read(target/'generation.json')['override_sha256']
   for p in (src/'ipcore').rglob('*'):
    if p.is_file() and p.suffix in ('.v','.idf'):assert sha(p)==sha(target/'ipcore'/p.relative_to(src/'ipcore'))
   inputs +=[tool,src/'generation.json',target/'generation.json'];tests +=['PASS exact '+name+' RTL/PLL/RAM regeneration']
 (out/(a.mode+'.json')).write_text(json.dumps(dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print(a.mode,'PASS')
if __name__=='__main__':main()
