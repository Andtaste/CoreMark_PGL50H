"""Apply the common audit to the explicit LW-only return qualifier."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 variant='dual_legacy_word';base=ROOT/'tools/check_dual_legacy.py';s=base.read_text().replace("assert 'rsp_valid && !rsp_error && !kill && !exception && kind==4 && wr && rd!=0' in mem","assert 'rsp_valid && !rsp_error && !kill && !exception && kind==4 && load_word && wr && rd!=0' in mem and 'return_data=rsp_data' in mem")
 ns={'__file__':str(base),'__name__':'word_audit'};exec(compile(s,str(base),'exec'),ns);sys.argv=[str(base),'--variant',variant,'--mode','audit'];ns['main']()
 p=ROOT/f'simulation/results/load_bp_{variant}/audit_checks/result.json';x=json.loads(p.read_text());x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
