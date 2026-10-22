"""Verify independent WB-only change, unchanged counters, exact reconstruction."""
from pathlib import Path
import contextlib,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 out=ROOT/'simulation/results/dual_wb_flags_verify';out.mkdir(exist_ok=False);accepted=ROOT/'docs/accepted_dual_baseline.json';a=read(accepted);assert a['variant']=='dual_boundary_storewrite';ref=ROOT/a['source_directory'];src=ref.with_name('load_bp_dual_boundary_wbflags');g=read(src/'generation.json');assert g['accepted_dual_sha256']==sha(accepted);inputs=[Path(__file__).resolve(),accepted];tests=[];changed=[]
 for key,h in g['override_sha256'].items():
  p=src/Path(key).name;assert sha(p)==h;inputs +=[p,ref/p.name]
  if h!=sha(ref/p.name):changed.append(p.name)
 assert changed==['nc_core.v'],changed
 for phase in ('performance','validation'):
  p=src/phase/'result.json';q=ref/phase/'result.json';x=read(p);y=read(q);assert x['status']==y['status']=='PASS'
  for key in ('metrics','predictor','multiply','dual','joint','boundary','mem_ipc','load_queue','store_followers'):assert x[key]==y[key],(phase,key)
  inputs +=[p,q];tests.append('PASS '+phase+' all measured counters identical to accepted')
 p=src/'wb_flag_proof/result.json';assert read(p)['status']=='PASS';inputs.append(p);tests.append('PASS actual capture-block induction, no cycle/exception/pairing change; all other RTL exact accepted hash')
 gen=ROOT/'tools/generate_dual_wb_flags.py';s=gen.read_text();pattern="out=src.with_name('load_bp_dual_boundary_wbflags')";assert s.count(pattern)==1;target=out/'reproduced';s=s.replace(pattern,'out=Path('+repr(str(target))+')');ns={'__file__':str(gen),'__name__':'wb_reproduction'};exec(compile(s,str(gen),'exec'),ns)
 with (out/'reproduction.log').open('w') as log,contextlib.redirect_stdout(log):ns['main']()
 assert g['override_sha256']==read(target/'generation.json')['override_sha256']
 for p in (src/'ipcore').rglob('*'):
  if p.is_file() and p.suffix in ('.v','.idf'):assert sha(p)==sha(target/'ipcore'/p.relative_to(src/'ipcore'))
 inputs +=[gen,src/'generation.json',target/'generation.json'];tests.append('PASS exact RTL/PLL/RAM reconstruction')
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print('WB flag counters and reproduction PASS')
if __name__=='__main__':main()
