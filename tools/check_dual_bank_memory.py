"""Prove all original MEM outputs plus per-bank published request contract."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);ref=ROOT/'simulation/results/load_bp_dual_boundary_storewrite';out=src/'bank_memory_proof';out.mkdir(exist_ok=True);inputs=[Path(__file__).resolve()];tests=[]
 for folder,label in ((ref,'gold'),(src,'gate')):
  p=folder/'nc_memory.v';s=p.read_text().replace('module nc_memory #','module '+label+'_mem #')
  if label=='gold':
   s=s.replace(' input wire[31:0] launch_address,',' output wire[1:0] req_banks,\n input wire[31:0] launch_address,');s=s.replace('endmodule', '''assign req_banks={2{req_valid}} & {(req_addr>=32'h10000000 && req_addr<32'h10008000),req_addr<32'h00010000};
 endmodule''')
  f=out/(label+'.v');f.write_text(s);inputs +=[p,f]
 def linux(p):return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
 for early in (0,1):
  for post in (0,1):
   script='read_verilog -sv '+linux(out/'gold.v')+' '+linux(out/'gate.v')+f'; chparam -set EARLY_REQUEST {early} -set POST_LOCAL_STORES {post} gold_mem; chparam -set EARLY_REQUEST {early} -set POST_LOCAL_STORES {post} gate_mem; proc; memory; async2sync; equiv_make gold_mem gate_mem equiv; hierarchy -top equiv; equiv_simple; equiv_induct -seq 2; equiv_status -assert'
   x=subprocess.run(['wsl.exe','-d','Ubuntu','--','yosys','-p',script],cwd=ROOT,capture_output=True,timeout=180);(out/f'e{early}_p{post}.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0,(x.stdout+x.stderr)[-2000:];tests.append(f'PASS actual full MEM sequential equivalence and req_banks == req_valid & selected-address bank, EARLY={early},POST={post}')
 (out/'result.json').write_text(json.dumps(dict(status='PASS',tests=tests,input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print(a.variant,'MEM/bank contract equivalence PASS 4')
if __name__=='__main__':main()
