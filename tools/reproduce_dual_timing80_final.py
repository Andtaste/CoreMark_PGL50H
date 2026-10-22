"""Verify exact final integration generator output without changing live results."""
from pathlib import Path
import hashlib,json,contextlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/load_bp_dual_boundary_uart';out=ROOT/'simulation/results/dual_timing80_repro/uart';tool=ROOT/'tools/generate_dual_timing80_uart.py';s=tool.read_text();old="out=src.with_name('load_bp_dual_boundary_uart')";assert s.count(old)==1;s=s.replace(old,'out=Path('+repr(str(out))+')');ns={'__file__':str(tool),'__name__':'timing80_repro_final'};exec(compile(s,str(tool),'exec'),ns)
 with (out.parent/'uart.log').open('w') as f,contextlib.redirect_stdout(f):ns['main']()
 g=json.loads((src/'generation.json').read_text());r=json.loads((out/'generation.json').read_text());assert g['override_sha256']==r['override_sha256']
 ips={str(p.relative_to(src/'ipcore')):sha(p) for p in (src/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')}
 for n,h in ips.items():assert sha(out/'ipcore'/n)==h,n
 inputs=[Path(__file__).resolve(),tool,src/'generation.json',out/'generation.json'];p=out.parent/'final_result.json';p.write_text(json.dumps(dict(status='PASS',override_sha256=r['override_sha256'],vendor_ip_sha256=ips,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print('PASS exact final RTL/PLL/RAM regeneration')
if __name__=='__main__':main()
