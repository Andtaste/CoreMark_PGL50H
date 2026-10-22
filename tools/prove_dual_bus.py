"""SAT proof of actual RTL acceptance and RAM enable cones, all 32-bit addresses."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def linux(p):p=p.resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def cone(path,name):
 s=path.read_text();part=s[s.index(' wire ib0='):s.index(' assign iov=')]
 keep=[]
 # Slice declarations/equations directly out of the exercised RTL, rather
 # than retype a separate boolean model of the intended implementation.
 for line in part.splitlines():
  if line.startswith(' reg ') or 'wire[63:0] iq0' in line or 'nc_uart #' in line or 'wire uart_send=' in line:continue
  line=line.replace('wire uart_ready;','')
  keep.append(line)
 ces=re.findall(r'\.[ab]_clk_en\((.*?)\),',s)
 assert len(ces)==4,ces
 return ('module '+name+'(input wire rst_n,iv,ior,dv,dor,dwrite,ipending,dpending,uart_ready,input wire[31:0] ia,da,\n'
  ' output wire[6:0] observable);\n'+'\n'.join(keep)+'\nassign observable={dr,ir,ia_fire,'+','.join(ces)+'};\nendmodule\n').replace('output wire[6:0] observable);','output wire[6:0] observable);\nwire dr,ir;')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_bus_split','dual_bus_local'),required=True);a=ap.parse_args()
 out=ROOT/('simulation/results/load_bp_'+a.variant);dest=out/'bus_formal';dest.mkdir(exist_ok=True)
 ref=ROOT/'simulation/results/load_bp_dual_ram_logic/nc_local_bus.v';new=out/'nc_local_bus.v';p=dest/'cones.v'
 p.write_text(cone(ref,'reference_cone')+cone(new,'candidate_cone')+'''
module proof(input wire rst_n,iv,ior,dv,dor,dwrite,ipending,dpending,uart_ready,input wire[31:0] ia,da,output wire equal);
 wire[6:0] a,b;
 reference_cone r(.*,.observable(a));candidate_cone c(.*,.observable(b));
 assign equal=a==b;
endmodule
''')
 command='read_verilog -sv '+linux(p)+'; prep -top proof -flatten; sat -verify -prove equal 1 -show-inputs -show-outputs'
 cmd=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--','yosys','-Q','-T','-p',command]
 x=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=180);log=x.stdout+x.stderr;(dest/'proof.log').write_bytes(log)
 assert x.returncode==0 and b'SUCCESS' in log,log[-5000:]
 r=dict(status='PASS',variant=a.variant,tests=['PASS SAT: original and candidate dr/ir/ia_fire/four RAM enables equal for every binary input and all 32-bit addresses'],
  scope='Combinational control cones extracted from actual RTL. Does not claim full sequential CPU formal verification.',command=cmd,input_sha256={str(q.relative_to(ROOT)):sha(q) for q in (ref,new,p,Path(__file__).resolve())})
 (dest/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(r['tests'][0])
if __name__=='__main__':main()
