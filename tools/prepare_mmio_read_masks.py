"""Expose mutually exclusive MMIO read masks on the measured late read path."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'simulation/results/autonomous_20261022'

def main():
 manifest=ROOT/'docs/active_optimization_baseline.json'
 m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 for name,digest in m['input_sha256'].items():
  assert hashlib.sha256((src/name).read_bytes()).hexdigest()==digest,name
 dest=WORK/'mmio_read_masks';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):
  shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(manifest,dest/'parent_baseline.json')
 p=dest/'source/sys_bus/nc_local_bus.v';s=p.read_text()
 start=s.index(' reg mmio_known;reg[31:0] read_mmio;')
 end=s.index(' integer j;',start)
 old=s[start:end]
 assert 'case(da)' in old and 'default:mmio_known=0;' in old
 pairs=[('20000000',"32'b0"),('20000004',"{31'b0,uart_ready}"),('20001000','mtime[31:0]'),('20001004','mtime[63:32]'),('20001008','mtimecmp[31:0]'),('2000100c','mtimecmp[63:32]'),('20002000',"{30'b0,gpio}"),('20003000','tohost')]
 lines=[' // Each read address is exclusive; preserve zero for unknown addresses.',' wire[7:0] mmio_select;']
 for i,(address,value) in enumerate(pairs):
  lines.append(f" assign mmio_select[{i}]=da==32'h{address};")
 lines.append(' wire mmio_known=|mmio_select;')
 terms=[f'({{32{{mmio_select[{i}]}}}} & {value})' for i,(_,value) in enumerate(pairs) if i]
 lines.append(' wire[31:0] read_mmio='+' |\n  '.join(terms)+';')
 p.write_text(s[:start]+'\n'.join(lines)+'\n'+s[end:])
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=m['source_trial'],intent='Explicit parallel masks for distinct MMIO read addresses; unchanged read sampling, errors and write side effects'),indent=2)+'\n')
 print('PREPARED',dest.name)

if __name__=='__main__':main()
