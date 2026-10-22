"""Include every preserved physical head pointer in the routed query."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=ROOT/'tools/report_dual_forward_paths.py';s=p.read_text();s=s.replace('soc/cpu/operands/rd/*/CLK}','soc/cpu/operands/rd/*/CLK soc/cpu/operands/local_rd*/*/CLK}')
 marker=" common='report_timing";assert s.count(marker)==1
 extra=" for i in range(6):queries['pointer_'+str(i)]=' -from {soc/cpu/operands/local_rd['+str(i)+']/*/CLK}'\n queries['pointer_original']=' -from {soc/cpu/operands/rd/*/CLK}'\n"
 s=s.replace(marker,extra+marker);ns={'__file__':str(p),'__name__':'head_local_paths'};exec(compile(s,str(p),'exec'),ns);sys.argv=[str(p),'--variant','dual_boundary_headlocal'];ns['main']()
 out=ROOT/'simulation/results/dual_forward_control_paths/dual_boundary_headlocal/result.json';x=json.loads(out.read_text())
 for i in range(6):
  for row in x['paths']['pointer_'+str(i)]:assert row['start'].startswith('soc/cpu/operands/local_rd['+str(i)+']/'),row
 for row in x['paths']['pointer_original']:assert row['start'].startswith('soc/cpu/operands/rd/'),row
 x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();x['scope']+='; head_control includes original rd and all six local copies; pointer0..5/original individually query all endpoints and assert actual startpoint identity';out.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
