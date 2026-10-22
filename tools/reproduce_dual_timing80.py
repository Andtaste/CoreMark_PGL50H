"""Rebuild generators into scratch directories and compare exact hardware inputs."""
from pathlib import Path
import hashlib,json,sys,contextlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 dest=ROOT/'simulation/results/dual_timing80_repro';dest.mkdir(exist_ok=False);rows={};inputs=[Path(__file__).resolve()]
 for suffix in ('side','pair'):
  src=ROOT/('simulation/results/load_bp_dual_boundary_'+suffix);target=dest/suffix;tool=ROOT/('tools/generate_dual_timing80'+('_pair' if suffix=='pair' else '')+'.py');s=tool.read_text()
  old="out=src.with_name('load_bp_dual_boundary_pair')" if suffix=='pair' else "out=src.with_name('load_bp_'+a.variant)";assert s.count(old)==1;s=s.replace(old,'out=Path('+repr(str(target))+')')
  ns={'__file__':str(tool),'__name__':'timing80_repro'};exec(compile(s,str(tool),'exec'),ns);sys.argv=[str(tool)]+(['--variant','dual_boundary_side'] if suffix=='side' else [])
  with (dest/(suffix+'.log')).open('w') as f,contextlib.redirect_stdout(f):ns['main']()
  g=json.loads((src/'generation.json').read_text());r=json.loads((target/'generation.json').read_text());assert g['override_sha256']==r['override_sha256']
  ips={str(p.relative_to(src/'ipcore')):sha(p) for p in (src/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')}
  for n,h in ips.items():assert sha(target/'ipcore'/n)==h,n
  rows[suffix]=dict(status='PASS',override_sha256=r['override_sha256'],vendor_ip_sha256=ips);inputs +=[tool,src/'generation.json',target/'generation.json']
 (dest/'result.json').write_text(json.dumps(dict(status='PASS',variants=rows,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print('PASS exact regeneration side/pair RTL and PLL/RAM inputs')
if __name__=='__main__':main()
