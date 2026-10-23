"""Validate two promising resolved-trace rankings in the actual RTL pipeline."""
from pathlib import Path
import argparse,hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'simulation/results/autonomous_20261022'
def main():
 parser=argparse.ArgumentParser()
 parser.add_argument('--shift',type=int,choices=range(8,15))
 parser.add_argument('--rotate',type=int,choices=range(1,5))
 args=parser.parse_args()
 assert (args.shift is None)==(args.rotate is None),'Supply both shift and rotate'
 manifest=ROOT/'docs/active_optimization_baseline.json';m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 for n,h in m['input_sha256'].items():assert hashlib.sha256((src/n).read_bytes()).hexdigest()==h,n
 ranking=json.loads((WORK/'btb_hash_profile/result.json').read_text());assert ranking['baseline']==m['variant']
 for shift,rotate in ([(args.shift,args.rotate)] if args.shift is not None else [(12,2),(11,1)]):
  dest=WORK/f'hash{shift}r{rotate}';assert not dest.exists();dest.mkdir()
  for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
  (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
  shutil.copyfile(manifest,dest/'parent_baseline.json')
  p=dest/'source/core/nc_btb.v';s=p.read_text()
  for pc in ('lookup_pc','update_pc'):
   old=f'{pc}[7:3]^{pc}[14:10]';assert s.count(old)==1
   split=shift+5-rotate
   low=f'{pc}[{split-1}:{shift}]';high=f'{pc}[{shift+4}:{split}]' if rotate>1 else f'{pc}[{split}]'
   s=s.replace(old,f'{pc}[7:3]^{{{low},{high}}}')
  p.write_text(s)
  (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
  (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=m['source_trial'],shift=shift,rotate=rotate,ranking_source='btb_hash_profile/result.json',intent='Same capacity, full tag, and counter/history design; change only XOR wiring'),indent=2)+'\n')
  print('PREPARED',dest.name)
if __name__=='__main__':main()
