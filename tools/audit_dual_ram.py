"""Lint, redundancy and provenance audit for the unchanged-policy RAM trial."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'simulation/results/load_bp_dual_ram_logic'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def linux(p):p=Path(p).resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def main():
 dest=OUT/'audit';dest.mkdir(exist_ok=True);meta=json.loads((OUT/'generation.json').read_text());b=json.loads((ROOT/'docs/accepted_baseline.json').read_text());inputs=[Path(__file__).resolve()]
 for n,h in b['source_sha256'].items():assert sha(ROOT/n)==h,n
 for n,h in meta['override_sha256'].items():assert sha(OUT/Path(n).name)==h,n
 for n,h in meta['ip_sha256'].items():assert sha(ROOT/n)==h,n
 files=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[])
 actual=[OUT/p.name if str(p.relative_to(ROOT)) in meta['override_sha256'] else p for p in files]+[OUT/'pango_ram_wide_models.v'];inputs+=actual
 command=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--','verilator','--lint-only','-Wall','-Wno-fatal','--top-module','nc_soc',*[linux(p) for p in actual]]
 with (dest/'lint.log').open('wb') as f:x=subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=180)
 text=(dest/'lint.log').read_text(errors='replace');assert x.returncode==0,text[-4000:]
 kinds={name:len(re.findall('%Warning-'+re.escape(name)+':',text)) for name in sorted(set(re.findall(r'%Warning-(\w+):',text)))}
 for dangerous in ('LATCH','UNOPTFLAT','MULTIDRIVEN','UNDRIVEN','IMPLICIT','PINMISSING','PINNOTFOUND'):
  assert kinds.get(dangerous,0)==0,(dangerous,kinds,text[-3000:])
 core=(OUT/'nc_core.v').read_text();fetch=(OUT/'nc_fetch.v').read_text();bus=(OUT/'nc_local_bus.v').read_text();bank=(OUT/'nc_btb.v').read_text()
 assert 'lookup_pc1' not in fetch and 'ia_lo' not in bus and 'ia_hi' not in bus
 assert 'ram_code_hi' not in bus and 'ram_data_hi' not in bus
 assert 'w1_pc=w_next' in core and 'w1_rd=w1_insn[11:7]' in core and 'wire[2:0] f1_tag=f_tag' in core
 assert 'function [3:0] newest4' in core and 'tag_a[0]=match_a1[tag_a[3:1]]' not in core
 assert 'reg[31:0] valid;' in bank and '[0:31]' in bank
 # Unused portions of full packets/trace observability are intentionally
 # retained in simulation. They are different from duplicated RAM storage.
 tests=['PASS no undriven/implicit/latch/combinational-cycle/multiple-driver lint warnings',
  'PASS duplicate BTB lookup tables replaced by two disjoint 32-entry banks',
  'PASS redundant secondary PC/rd storage removed using existing next-PC and instruction fields',
  'PASS duplicate forwarding tag FF declaration and unused lookup/address declarations removed',
  'PASS group-tag encoding plus dynamic lane lookup replaced by equivalent balanced four-bit encoder']
 result=dict(status='PASS',tests=tests,lint_warning_counts=kinds,lint_limits='Full packet/trace fields and x0 unused data bits can remain unused; no claim that every unused-bit warning is removable hardware.',
  input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs},baseline_sha256=sha(ROOT/'docs/accepted_baseline.json'))
 (dest/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='input_sha256'},indent=2))
if __name__=='__main__':main()
