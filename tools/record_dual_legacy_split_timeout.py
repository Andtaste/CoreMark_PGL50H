"""Record the 900s PDS timeout; do not invent routed frequency/slack."""
from pathlib import Path
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/load_bp_dual_legacy_split';work=src/'pds';assert not (work/'result.json').exists() or json.loads((work/'result.json').read_text())['status']=='PDS_TIMEOUT';assert not (work/'report_timing/top.rtr').exists()
 g=json.loads((src/'generation.json').read_text());inputs=[work/'run.tcl',work/'build.log',work/'device_map/top.dmr',Path(__file__).resolve(),ROOT/'tools/research_dual_ram_pds.py']
 for n,h in g['override_sha256'].items():p=src/Path(n).name;assert sha(p)==h;inputs.append(p)
 resource=(work/'device_map/top.dmr').read_text(errors='replace')
 x=dict(status='PDS_TIMEOUT',variant='dual_legacy_split',timeout_seconds=900,pds_exit_code=None,estimated_fmax_mhz=None,corners=None,resources={k:int(re.search(r'\| '+re.escape(k)+r'\s+\|\s+(\d+)',resource)[1]) for k in ('LUT','FF','Distributed RAM','DRM','APM')},tcl_sha256=sha(work/'run.tcl'),production_preserved=True,scope='Synthesis/map completed; detailed router still had unrouted nets at Python 900s timeout. Command-line inventory confirmed no remaining candidate PDS process during cleanup. No timing closure/frequency claim, no seed rerun.',input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs})
 (work/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x,indent=2)[:1100])
if __name__=='__main__':main()
