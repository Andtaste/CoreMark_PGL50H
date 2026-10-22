"""Prove actual MEM publication contract for arbitrary input/state bits."""
from pathlib import Path
import argparse,hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();src=ROOT/('simulation/results/load_bp_'+a.variant);out=src/'publication_proof';out.mkdir(exist_ok=True);actual=src/'nc_memory.v';s=actual.read_text();needle='input wire rsp_error);';assert s.count(needle)==1;s=s.replace(needle,'input wire rsp_error,output wire publication_ok);');s=s.replace('endmodule','assign publication_ok=!req_write || (req_valid && req_addr==write_address);\nendmodule');p=out/'publication.v';p.write_text(s)
 def linux(p):return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
 script='read_verilog -sv '+linux(p)+'; chparam -set EARLY_REQUEST 1 -set POST_LOCAL_STORES 1 nc_memory; prep -top nc_memory -flatten; async2sync; opt; sat -verify -seq 1 -prove publication_ok 1'
 x=subprocess.run(['wsl.exe','-d','Ubuntu','--','yosys','-p',script],cwd=ROOT,capture_output=True,timeout=180);(out/'sat.log').write_bytes(x.stdout+x.stderr);assert x.returncode==0 and b'SUCCESS!' in x.stdout
 inputs=[Path(__file__).resolve(),actual,p];(out/'result.json').write_text(json.dumps(dict(status='PASS',tests=['PASS actual MEM all-state publication: req_write implies req_valid and selected address equals held write_address; no reset/reachability assumptions'],input_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs}),indent=2)+'\n');print(a.variant,'publication SAT PASS')
if __name__=='__main__':main()
