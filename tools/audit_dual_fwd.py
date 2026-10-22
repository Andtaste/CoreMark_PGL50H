"""Constrain forwarding trials to local data selection and capture changes."""
from pathlib import Path
import argparse,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def normalized(s,mask,shared):
 if mask:
  for op,wait in (('a','wa'),('b','wb')):
   start=s.index('  // Exclusive priority masks')
   end=s.index(';',s.index(f'  assign selected_v{op}[s]=',start))+1
   old=f'  assign selected_v{op}[s]={wait}[s] ? (hit_f{op}[s] ? f_data : hit_f1{op}[s] ? f1_data : hit_m{op}[s] ? m_data : hit_w{op}[s] ? w_data : w1_data) : v{op}[s];'
   s=s[:start]+old+s[end:]
 if shared:
  for op,wait in (('a','wa'),('b','wb')):
   old=f'   if({wait}[i] && available_{op}[i]) begin v{op}[i]<=selected_v{op}[i];{wait}[i]<=0;end'
   lines=[]
   for i,(h,d) in enumerate((('f','f_data'),('f1','f1_data'),('m','m_data'),('w','w_data'),('w1','w1_data'))):
    lines.append(f'   {"if" if i==0 else "else if"}({wait}[i] && hit_{h}{op}[i]) begin v{op}[i]<={d};{wait}[i]<=0;end')
   assert old in s;s=s.replace(old,'\n'.join(lines))
 return s
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args()
 parent=ROOT/'simulation/results/load_bp_dual_if_parts';src=parent.with_name('load_bp_'+a.variant)
 meta=json.loads((src/'generation.json').read_text());pm=json.loads((parent/'generation.json').read_text())
 assert meta['override_sha256'].keys()==pm['override_sha256'].keys()
 for n,h in meta['override_sha256'].items():
  assert sha(src/Path(n).name)==h,n
  if Path(n).name!='nc_operands.v':assert sha(src/Path(n).name)==sha(parent/Path(n).name),n
 old=(parent/'nc_operands.v').read_text();new=(src/'nc_operands.v').read_text()
 assert normalized(new,True,a.variant=='dual_fwd_share')==old
 out=src/'boundary_audit';out.mkdir(exist_ok=True)
 x=dict(status='PASS',tests=[
  'PASS exact textual equivalence after reversing only the local priority-data selection/capture transformations',
  'PASS all five encoded tag comparisons, insertion forwarding, output availability, ready/pop/push, reset/clear and queue state unchanged',
  'PASS all other overridden modules byte-identical to retained parent'],
  limits='Static change-scope check, not a routed timing or full functional proof; paired with SAT, cycle equivalence, full regression and routed STA.',
  input_sha256={str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__).resolve(),parent/'nc_operands.v',src/'nc_operands.v',parent/'generation.json',src/'generation.json')})
 (out/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(a.variant,'PASS boundary audit')
if __name__=='__main__':main()
