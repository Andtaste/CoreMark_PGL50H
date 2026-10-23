"""Compare predictor state sizes on the accepted folded-index hardware."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'simulation/results/autonomous_20261022'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 manifest=ROOT/'docs/active_optimization_baseline.json';m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 for n,h in m['input_sha256'].items():assert sha(src/n)==h,n
 for name in ('history2','bimodal'):
  dest=WORK/name;assert not dest.exists(),dest;dest.mkdir()
  for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
  s=re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text());(dest/'new_core.pds').write_text(s)
  shutil.copyfile(manifest,dest/'parent_baseline.json')
  p=dest/'source/core/nc_btb.v';s=p.read_text()
  if name=='history2':
   s=s.replace('reg[4:0] directions','reg[9:0] directions').replace('wire[4:0] read_direction','wire[9:0] read_direction').replace('wire[4:0] old_direction','wire[9:0] old_direction')
   s=s.replace('read_direction[4] ? read_direction[3] : read_direction[1]',"read_direction[{read_direction[9:8],1'b1}]")
   s=s.replace('old_direction[4] ? old_direction[3:2] : old_direction[1:0]',"old_direction[{old_direction[9:8],1'b0} +: 2]")
   old="""directions[w]<=!update_conditional ? 5'b01111 : !same_entry ?
    {update_taken,{2{update_taken ? 2'b10 : 2'b01}}} :
    {update_taken,(old_direction[4] ? trained : old_direction[3:2]),
                  (old_direction[4] ? old_direction[1:0] : trained)};"""
   new="""directions[w]<=!update_conditional ? 10'b0011111111 : !same_entry ?
    {1'b0,update_taken,{4{update_taken ? 2'b10 : 2'b01}}} :
    {old_direction[8],update_taken,
     (old_direction[9:8]==3 ? trained : old_direction[7:6]),
     (old_direction[9:8]==2 ? trained : old_direction[5:4]),
     (old_direction[9:8]==1 ? trained : old_direction[3:2]),
     (old_direction[9:8]==0 ? trained : old_direction[1:0])};"""
   assert s.count(old)==1;s=s.replace(old,new).replace('// {last resolved outcome, counter after taken, counter after not-taken}.','// Two resolved history bits select four independent two-bit counters.')
  else:
   s=s.replace('reg[4:0] directions','reg[1:0] directions').replace('wire[4:0] read_direction','wire[1:0] read_direction').replace('wire[4:0] old_direction','wire[1:0] old_direction')
   s=s.replace('read_direction[4] ? read_direction[3] : read_direction[1]','read_direction[1]').replace('old_direction[4] ? old_direction[3:2] : old_direction[1:0]','old_direction')
   s,n=re.subn(r'directions\[w\]<=.*?;','directions[w]<=!update_conditional ? 2\'b11 : !same_entry ? (update_taken ? 2\'b10 : 2\'b01) : trained;',s,flags=re.S);assert n==1
   s=s.replace('// {last resolved outcome, counter after taken, counter after not-taken}.','// One saturating two-bit counter per entry; no local history.')
  p.write_text(s)
  (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):sha(p) for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
  print('PREPARED',name)
if __name__=='__main__':main()
