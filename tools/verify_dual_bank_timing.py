"""Check identical schedules, source scope, dead-code audit and regeneration."""
from pathlib import Path
import contextlib,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 out=ROOT/'simulation/results/dual_bank_timing_verify';out.mkdir(exist_ok=False);accepted=ROOT/'docs/accepted_dual_baseline.json';a=read(accepted);assert a['variant']=='dual_boundary_storewrite';ref=ROOT/a['source_directory'];inputs=[Path(__file__).resolve(),accepted];tests=[]
 for name,toolname,pattern in (
  ('bankreq','generate_dual_bank_timing.py',"out=src.with_name('load_bp_'+a.variant)"),
  ('banklocal','generate_dual_bank_local.py',"out=src.with_name('load_bp_dual_boundary_banklocal')")):
  src=ROOT/('simulation/results/load_bp_dual_boundary_'+name);g=read(src/'generation.json');assert g['accepted_dual_sha256']==sha(accepted);changed=[]
  for key,h in g['override_sha256'].items():
   p=src/Path(key).name;assert sha(p)==h;inputs.append(p)
   if sha(ref/p.name)!=h:changed.append(p.name)
  assert set(changed)=={'nc_core.v','nc_memory.v','nc_local_bus.v','nc_soc.v'},changed
  for phase in ('performance','validation'):
   p=src/phase/'result.json';r=ref/phase/'result.json';x=read(p);y=read(r);assert x['status']==y['status']=='PASS'
   for key in ('metrics','predictor','multiply','dual','joint','boundary','mem_ipc','load_queue','store_followers'):assert x[key]==y[key],(name,phase,key)
   inputs +=[p,r];tests.append('PASS '+name+' '+phase+' all measured counters identical to accepted')
  for sub,count in (('bank_memory_proof',4),('bank_bus_proof',2)):
   p=src/sub/'result.json';assert read(p)['status']=='PASS' and len(read(p)['tests'])==count;inputs.append(p)
  gen=ROOT/'tools'/toolname;s=gen.read_text();assert s.count(pattern)==1;target=out/name;s=s.replace(pattern,'out=Path('+repr(str(target))+')');ns={'__file__':str(gen),'__name__':'bank_regeneration'};exec(compile(s,str(gen),'exec'),ns);sys.argv=[str(gen),'--variant','dual_boundary_'+name]
  with (out/(name+'.log')).open('w') as log,contextlib.redirect_stdout(log):ns['main']()
  assert g['override_sha256']==read(target/'generation.json')['override_sha256']
  for p in (src/'ipcore').rglob('*'):
   if p.is_file() and p.suffix in ('.v','.idf'):assert sha(p)==sha(target/'ipcore'/p.relative_to(src/'ipcore'))
  inputs +=[gen,src/'generation.json',target/'generation.json'];tests.append('PASS '+name+' exact RTL/PLL/RAM reconstruction, only4 interface/control source files changed')
 ev=ROOT/'simulation/results/load_bp_dual_boundary_slots/operand_checks/result.json';assert read(ev)['cycles']==300000 and read(ev)['status']=='PASS';assert sha(ref/'nc_operands.v')==sha(ev.parent.parent/'nc_operands.v');inputs.append(ev);tests.append('PASS unchanged operand implementation reuses independent300000-cycle equivalence')
 net=ref/'pds/synthesize/top_syn.vm';nettext=net.read_text(errors='replace');inputs.append(net);audit=[]
 for filename,n,expected,meaning in (
  ('nc_core.v','inflight',1,'Unconsumed population-count debug wire'),('nc_core.v','resolved_prediction',1,'Unconsumed target-selection wire'),('nc_core.v','mul_busy',2,'Unused multiplier busy output connection'),('nc_core.v','second_dep',3,'Assigned constant0, retained for legacy bench observability'),('nc_memory.v','request_data',1,'Unconsumed request payload alternative'),('nc_memory.v','request_f3',1,'Unconsumed request format alternative'),('nc_memory.v','state',1,'Combinational state label used only by observation'),('nc_mul_pipeline.v','low2',2,'Assigned32-bit register never consumed')):
  p=ref/filename;text=p.read_text();count=len(re.findall(r'\b'+n+r'\b',text));assert count==expected,(n,count);prefix='memory/' if filename=='nc_memory.v' else 'multiply/' if filename=='nc_mul_pipeline.v' else '';audit.append(dict(source=filename,signal=n,source_mentions=count,classification=meaning,synthesis_named_node_present=('soc/cpu/'+prefix+n) in nettext,note='Source cleanup only; unused/constant logic is removed by synthesis. No claimed LUT/FF gain from deleting these names.'));inputs.append(p)
 (out/'redundancy_audit.json').write_text(json.dumps(dict(status='PASS',entries=audit,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in set(inputs) if p in [net,ref/'nc_core.v',ref/'nc_memory.v',ref/'nc_mul_pipeline.v']}),indent=2)+'\n')
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print('Bank timing evidence, audit and reconstruction PASS')
if __name__=='__main__':main()
