"""Select primary-A broadcast masks before wide data selection at the queue head."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'simulation/results/autonomous_20261022'

def main():
 manifest=ROOT/'docs/active_optimization_baseline.json'
 m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 for name,digest in m['input_sha256'].items():
  assert hashlib.sha256((src/name).read_bytes()).hexdigest()==digest,name
 dest=WORK/'operand_head_mux';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):
  shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(manifest,dest/'parent_baseline.json')
 p=dest/'source/core/nc_operands.v';s=p.read_text()
 old=' genvar s;';assert s.count(old)==1
 names=['use_a_'+x for x in ('f','f1','m','w','w1')]
 s=s.replace(old,' wire[1:0] '+','.join(names)+';\n'+old)
 for name in names:
  s,n=re.subn(r'wire '+name+r'=',f'assign {name}[s]=',s);assert n==1
  s,n=re.subn(r'\{32\{'+name+r'\}\}',r'{32{'+name+'[s]}}',s);assert n==1
 old=' wire[31:0] a=selected_va[rd],b=selected_vb[rd];';assert s.count(old)==1
 new=''' // Select narrow forwarding masks before distributing shared broadcast data.
 // Slot-local selection remains unchanged for operand capture during stalls.
 wire[31:0] a=({32{!wa[rd]}} & va[rd]) |
   ({32{use_a_f[rd]}} & f_data) | ({32{use_a_f1[rd]}} & f1_data) |
   ({32{use_a_m[rd]}} & m_data) | ({32{use_a_w[rd]}} & w_data) |
   ({32{use_a_w1[rd]}} & w1_data);
 wire[31:0] b=selected_vb[rd];'''
 p.write_text(s.replace(old,new))
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=m['source_trial'],intent='Primary A output selects narrow masks before broadcast data; preserve priority, capture, queue state and cycles'),indent=2)+'\n')
 print('PREPARED',dest.name)

if __name__=='__main__':main()
