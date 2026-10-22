"""Check empty-slot implementation integration and exact generated source."""
from pathlib import Path
import argparse,hashlib,json,contextlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=('metrics','uart','reproduce'),required=True);a=ap.parse_args();src=ROOT/'simulation/results/load_bp_dual_boundary_slots';out=src/('slots_'+a.mode);out.mkdir(exist_ok=True);inputs=[Path(__file__).resolve()];tests=[]
 if a.mode=='uart':
  base=ROOT/'tools/check_dual_timing80_uart.py';s=base.read_text().replace("'simulation/results/load_bp_dual_boundary_pair'","'simulation/results/load_bp_dual_boundary_slots'");ns={'__file__':str(base),'__name__':'slots_uart'};exec(compile(s,str(base),'exec'),ns);ns['main']();p=src/'uart80/result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__));p.write_text(json.dumps(x,indent=2)+'\n');return
 if a.mode=='metrics':
  ref=ROOT/'simulation/results/load_bp_dual_boundary_launch'
  for phase in ('performance','validation'):
   old=json.loads((ref/phase/'result.json').read_text());new=json.loads((src/phase/'result.json').read_text());assert new['status']=='PASS'
   for key in ('metrics','predictor','multiply','dual','boundary','joint'):assert old[key]==new[key],(phase,key)
   inputs +=[ref/phase/'result.json',src/phase/'result.json'];tests +=['PASS '+phase+' all counters and profile fields unchanged']
  p=src/'operand_checks/result.json';x=json.loads(p.read_text());assert x['status']=='PASS' and x['cycles']==300000;inputs.append(p);tests +=['PASS new operand implementation against independent direct-tag reference, 300000 cycles / 600000 edge checks']
 else:
  for suffix in ('preload','slots'):
   origin=src.with_name('load_bp_dual_boundary_'+suffix);target=ROOT/('simulation/results/dual_timing80_repro/'+suffix);tool=ROOT/('tools/generate_dual_timing80_'+suffix+'.py');s=tool.read_text();old="out=src.with_name('load_bp_dual_boundary_"+suffix+"')";assert s.count(old)==1;s=s.replace(old,'out=Path('+repr(str(target))+')');ns={'__file__':str(tool),'__name__':'slots_repro'};exec(compile(s,str(tool),'exec'),ns)
   with (out/(suffix+'.log')).open('w') as f,contextlib.redirect_stdout(f):ns['main']()
   g=json.loads((origin/'generation.json').read_text());r=json.loads((target/'generation.json').read_text());assert g['override_sha256']==r['override_sha256']
   for p in (origin/'ipcore').rglob('*'):
    if p.is_file() and p.suffix in ('.v','.idf'):assert sha(p)==sha(target/'ipcore'/p.relative_to(origin/'ipcore'))
   inputs +=[tool,origin/'generation.json',target/'generation.json'];tests +=['PASS exact '+suffix+' RTL/PLL/RAM regeneration']
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print(a.mode,'PASS')
if __name__=='__main__':main()
