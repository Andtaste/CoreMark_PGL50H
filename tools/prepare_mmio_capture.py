"""Remove accepted-request decode from the MMIO data capture enable."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'simulation/results/autonomous_20261022'

def main():
 manifest=ROOT/'docs/active_optimization_baseline.json'
 m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 for name,digest in m['input_sha256'].items():
  assert hashlib.sha256((src/name).read_bytes()).hexdigest()==digest,name
 dest=WORK/'mmio_capture';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):
  shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(manifest,dest/'parent_baseline.json')
 p=dest/'source/sys_bus/nc_local_bus.v';s=p.read_text()
 old='derror<=!(db0 || db1 || mmio_known);mmio_data<=read_mmio;';assert s.count(old)==1
 s=s.replace(old,'derror<=!(db0 || db1 || mmio_known);')
 old='   if(da_fire) begin';assert s.count(old)==1
 s=s.replace(old,'''   // An empty or consumed response slot may sample data before admission.
   // Pending stalled responses keep their original sampled MMIO value.
   if(!dpending || dor) mmio_data<=read_mmio;
'''+old)
 p.write_text(s)
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=m['source_trial'],intent='Free response-slot sampling for MMIO data; preserve accepted response values and stalled response stability; shorten request-valid to wide CE path'),indent=2)+'\n')
 print('PREPARED',dest.name)

if __name__=='__main__':main()
