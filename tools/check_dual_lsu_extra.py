"""Adapt older fault coverage to the LSU's pre-WB younger-slot suppression."""
from pathlib import Path
import json,sys,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 variant=sys.argv[1];src=ROOT/('simulation/results/load_bp_'+variant)
 base=ROOT/'tools/check_dual_native_extra.py';s=base.read_text().replace('f.classify(inst1)','f.classify_side(inst1)').replace('[105:74]','[106:75]')
 s=s.replace("executable=OUT/'checks'/(kind+'.vvp')",'''executable=dest/(kind+'.vvp')
  original=OUT/'checks'/(kind+'_tb.v');tb=dest/(kind+'_tb.v');cpu='dut' if kind=='core' else 'dut.cpu'
  text=original.read_text().replace(f'if({cpu}.do_trap && {cpu}.w_side[64])',f'if(({cpu}.do_trap && {cpu}.w_side[64]) || ({cpu}.memory.finished && {cpu}.memory.primary_error && {cpu}.memory.held_side[96]))')
  tb.write_text(text)
  files=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[])
  if kind=='core':files=[p for p in files if p.parent.name=='core']
  files=[OUT/p.name if str(p.relative_to(ROOT)) in overrides else p for p in files]
  if kind=='soc':files+=[OUT/'pango_ram_wide_models.v']
  inputs +=[tb,*files]
  run([iv,'-g2012','-s',kind+'_tb','-o',executable,*files,tb],kind+'_compile.log')''')
 ns={'__file__':str(base),'__name__':'lsu_extra'};exec(compile(s,str(base),'exec'),ns);ns['OUT']=src;sys.argv=[str(base)];ns['main']()
 p=src/'dual_checks/result.json';x=json.loads(p.read_text());x['coverage_note']='Count primary-fault younger suppression before WB, because LSU clears WB side valid on primary error. Assembly independently checks causes, EPC and unchanged younger destination.';x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
