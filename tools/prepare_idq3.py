"""Evaluate a three-slot operand queue with registered occupancy credit."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'simulation/results/autonomous_20261022'
def main():
 manifest=ROOT/'docs/active_optimization_baseline.json';m=json.loads(manifest.read_text());src=ROOT/m['project_directory']
 for n,h in m['input_sha256'].items():assert hashlib.sha256((src/n).read_bytes()).hexdigest()==h,n
 dest=WORK/'idq3';assert not dest.exists();dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
 (dest/'new_core.pds').write_text(re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text()))
 shutil.copyfile(manifest,dest/'parent_baseline.json')
 p=dest/'source/core/nc_operands.v';s=p.read_text()
 s=s.replace('Two-entry in-order','Three-entry in-order').replace('Both slots','All slots')
 s=s.replace('[0:1]','[0:2]').replace('reg[1:0]','reg[2:0]').replace('wire[1:0]','wire[2:0]')
 s=s.replace('reg rd,wr;reg[2:0] count;','reg[1:0] rd,wr;reg[1:0] count;')
 assert 'reg[1:0] rd,wr;' in s
 s=s.replace('s<2','s<3').replace('i<2','i<3').replace('wr==i[0]','wr==i[1:0]').replace('count!=2','count!=3')
 old="wire[2:0] free_slot={count==0 || (count==1 && !rd),count==0 || (count==1 && rd)};"
 assert s.count(old)==1
 s=s.replace(old,"""wire[2:0] free_slot;
 genvar q;
 generate for(q=0;q<3;q=q+1) begin:slot_free
  assign free_slot[q]=(count==0) || (count==1 && rd!=q[1:0]) || (count==2 && wr==q[1:0]);
 end endgenerate""")
 old='if(push) wr<=!wr;if(pop) rd<=!rd;';assert s.count(old)==1
 s=s.replace(old,"if(push) wr<=wr==2 ? 2'd0 : wr+2'd1;if(pop) rd<=rd==2 ? 2'd0 : rd+2'd1;")
 p.write_text(s)
 (dest/'inputs.json').write_text(json.dumps({str(p.relative_to(dest)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file()},indent=2)+'\n')
 (dest/'derivation.json').write_text(json.dumps(dict(parent_trial=m['source_trial'],intent='Three registered-credit operand slots; no combinational ready feedback or fallthrough'),indent=2)+'\n')
 print('PREPARED idq3')
if __name__=='__main__':main()
