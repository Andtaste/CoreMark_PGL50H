"""Rebuild isolated RTL/IP and verify accepted inputs and actual compile receipts."""
from pathlib import Path
import sys,json,hashlib,contextlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'simulation/results/dual_next_reproduction'
TRIALS=['mqual','fqual','mpre','loadsplitv2','pairmul','pairbranch','loadcapture','wordwake','loadwake','aluwake']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 OUT.mkdir(exist_ok=False);accepted=ROOT/'docs/accepted_dual_baseline.json';a=read(accepted);assert a['variant']=='dual_boundary_storewrite';ah=sha(accepted);assert ah=='b68472e674aa2d9e656485c85a450d7cbefcd060c96c26dd0ae8f7b61ee7882a'
 tests=[];inputs=[accepted,Path(__file__).resolve()]
 for k in ('source_sha256','ip_sha256','evidence_sha256'):
  for n,h in a[k].items():assert sha(ROOT/n)==h,(k,n)
 tests.append('PASS accepted descriptor/source/IP/evidence unchanged')
 for k,n in [('single_issue_reference_sha256','docs/accepted_baseline.json'),('single_issue_sta_sha256','hardware/pds/report_timing/top.rtr')]:assert sha(ROOT/n)==a[k]
 tests.append('PASS original single-issue descriptor and routed STA unchanged')
 generators={'fqual':'generate_dual_next_fqual.py','loadsplitv2':'generate_dual_next_loadsplit.py','loadcapture':'generate_dual_next_loadcapture.py','aluwake':'generate_dual_next_aluwake.py'}
 for t in TRIALS:
  src=ROOT/('simulation/results/load_bp_dual_boundary_next_'+t);g=read(src/'generation.json');assert g['accepted_dual_sha256']==ah
  gen=ROOT/'tools'/generators.get(t,'generate_dual_next_trials.py');assert sha(gen)==g['generator_sha256'];s=gen.read_text();pattern="out=src.with_name('load_bp_dual_boundary_next_"+(t+"')" if t in generators else "'+t)");assert s.count(pattern)==1,(t,pattern)
  target=OUT/t;s=s.replace(pattern,'out=Path('+repr(str(target))+')');ns={'__file__':str(gen),'__name__':'exact_reproduction'};exec(compile(s,str(gen),'exec'),ns);sys.argv=[str(gen),'--trial',t]
  with (OUT/(t+'.log')).open('w') as f,contextlib.redirect_stdout(f):ns['main']()
  assert read(target/'generation.json')['override_sha256']==g['override_sha256']
  for n,h in g['override_sha256'].items():assert sha(src/Path(n).name)==h
  for p in (src/'ipcore').rglob('*'):
   if p.is_file() and p.suffix in ('.v','.idf'):assert sha(p)==sha(target/'ipcore'/p.relative_to(src/'ipcore'))
  for phase in ('performance','validation','checks'):
   r=src/phase/'result.json';x=read(r);assert x['status']=='PASS';inputs.append(r)
   for k in ('input_sha256','actual_compile_sha256','ip_sha256'):
    for n,h in x.get(k,{}).items():assert (ROOT/n).is_file() and sha(ROOT/n)==h,(t,phase,k,n)
   if phase!='checks':
    ref=read(ROOT/a['source_directory']/phase/'result.json')
    for k in ('Retired instructions','Retired loads','Retired stores','BJP instructions','seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal'):assert x['metrics'][k]==ref['metrics'][k],(t,phase,k)
  c=(src/'nc_core.v').read_text();o=(src/'nc_operands.v').read_text();assert 'assign mem_credit=queue_credit;' in c and 'assign in_ready=count!=2;' in o
  inputs +=[gen,src/'generation.json',target/'generation.json'];tests.append('PASS '+t+' exact RTL/IP reproduction, actual compilation hashes, fixed1/10 CRC and architectural retirement totals, registered input credit')
 assert sha(accepted)==ah
 (OUT/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print('\n'.join(tests))
if __name__=='__main__':main()
