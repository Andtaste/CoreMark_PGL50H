"""Promote a fully verified comparison-fix implementation, preserving old main."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess
from verify_board_pnr import inspect,sha
ROOT=Path(__file__).resolve().parents[1]
def dump(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('candidate');a=ap.parse_args()
 src=(ROOT/a.candidate).resolve();assert src.is_relative_to(ROOT/'simulation/results')
 physical=inspect(src,83)
 base=ROOT/('simulation/results/report_compare_xor83_20261023' if 'xor83' in src.name else 'simulation/results/report_compare_fix83_20261023')
 for n in ('checks/result.json','rtl_equivalence/result.json'):assert json.loads((base/n).read_text())['status']=='PASS'
 assert sha(src/'source/core/nc_execute.v')==sha(base/'source/core/nc_execute.v')
 def logic(p):return re.sub(r'//[^\n]*','',(p/'synthesize/top_syn.vm').read_text())
 if logic(src)!=logic(base):
  replay=json.loads((src/'report_replay.json').read_text())
  assert replay['status']=='PASS' and replay['netlist_logic_sha256']==hashlib.sha256(logic(src).encode()).hexdigest()
  assert replay['execute_sha256']==sha(src/'source/core/nc_execute.v')
 assert json.loads((ROOT/'simulation/results/report_large_20261023/diagnosis.json').read_text())['status']=='PASS'
 main=ROOT/'hardware/pds';backup=ROOT/'hardware/pds_before_compare_fix_20261023'
 assert not backup.exists()
 old=json.loads((main/'main_manifest.json').read_text())
 for n,h in old['input_sha256'].items():
  if n not in ('source/core/nc_execute.v','new_core.tcl'):assert sha(src/n)==h,n
 s=(src/'new_core.pds').read_text()
 ps=int(re.search(r'\(_option gplace_seed \(_integer (\d+)\)\)',s)[1]);rs=int(re.search(r'\(_option groute_seed \(_integer (\d+)\)\)',s)[1])
 fanout=int(re.search(r'\(_option fanout_guide \(_integer (\d+)\)\)',s)[1])
 priority='(_option enable_route_constraint_iterate (_switch ON))' in s
 # The project directory may be held open by PDS or a terminal on Windows.
 # Preserve a complete copy before updating files in the existing directory.
 assert main.parent==backup.parent==ROOT/'hardware'
 shutil.copytree(main,backup)
 for n,h in old['input_sha256'].items():assert sha(backup/n)==h,n
 shutil.copytree(src,main,dirs_exist_ok=True)
 t=(backup/'new_core.tcl').read_text();t=re.sub(r'-gplace_seed \d+ -groute_seed \d+',f'-gplace_seed {ps} -groute_seed {rs}',t);t=re.sub(r'-fanout_guide \d+',f'-fanout_guide {fanout}',t);(main/'new_core.tcl').write_text(t)
 if priority:
  t=t.replace('-fix_hold_violation\n','-fix_hold_violation -enable_route_constraint_iterate -route_constraint_iterate_times 4 -route_constraint_slack 0.05 -route_constraint_max_timing_path 5\n');(main/'new_core.tcl').write_text(t)
 old.update(place_seed=ps,route_seed=rs,fanout_guide=fanout,priority_routing=priority,correctness_fix='explicit MSB signed/unsigned comparison')
 old['input_sha256']={n:sha(main/n) for n in old['input_sha256']};dump(main/'main_manifest.json',old)
 assert inspect(main,83)==physical
 with (main/'bitstream_build.log').open('wb') as f:subprocess.run(['E:/pango/PDS_2022.2-SP1-Lite/bin/pds_shell.exe','-f','generate_bitstream.tcl'],cwd=main,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300)
 assert not re.search(r'^E:',(main/'bitstream_build.log').read_text(errors='replace'),re.M)
 bit=main/'generate_bitstream/top.sbit';assert bit.stat().st_size>1000
 (main/'download').mkdir(exist_ok=True);shutil.copyfile(bit,main/'download/top.sbit')
 physical.update(configured_cpu_hz=83000000,iterations=5000,bitstream_sha256=sha(bit),bitstream='download/top.sbit',scope='Comparison correction: RTL regression and ADS gate report replay pass. Native 83MHz STA and bitstream generation pass. Not yet programmed on board.')
 dump(main/'release_result.json',physical)
 out=ROOT/'output/board83';shutil.copyfile(bit,out/'top.sbit');shutil.copyfile(main/'release_result.json',out/'release_result.json')
 profile=ROOT/'docs/active_compiler_profile.json';shutil.copyfile(profile,ROOT/'docs/compiler_profile_before_compare_fix.json')
 p=json.loads(profile.read_text());p['hardware'].update(project_directory='hardware/pds',place_seed=ps,route_seed=rs,input_sha256=old['input_sha256'],estimated_fmax_mhz=physical['estimated_fmax_mhz'],resources=physical['routed_resources'],physical_verification=physical,independent_native_runs=1)
 p['hardware']['implementation_options']['fanout_guide']=fanout
 p['hardware']['priority_routing']=priority
 p['correctness_revision']={'parent_profile':'docs/compiler_profile_before_compare_fix.json','rtl_patch':'source/core/nc_execute.v','evidence':'simulation/results/report_large_20261023/diagnosis.json','scope':'Historical RTL manifest retained as parent; current hardware adds explicit-sign comparison correction. Original firmware unchanged. Historical diagnostic cycle counts are not new fixed-hardware board measurements.'}
 p['scope']=physical['scope'];p['clock_adoption']['minimum_setup_slack_ns']=physical['corners']['Setup Summary(Slow Corner)']['worst_slack_ns'];p['clock_adoption']['decision']='Retain83MHz after comparison correctness fix; current physical evidence supersedes historical clock trial.';dump(profile,p)
 receipt=ROOT/'docs/main_board83_sync.json';shutil.copyfile(receipt,ROOT/'docs/main_board83_before_compare_fix.json')
 dump(receipt,{'status':'PASS','main_project':'hardware/pds/new_core.pds','previous_main':str(backup.relative_to(ROOT)),'configured_cpu_hz':83000000,'firmware_iterations':5000,'bitstream':'output/board83/top.sbit','bitstream_sha256':sha(bit),'fmax_mhz':physical['estimated_fmax_mhz'],'setup_slack_ns':physical['corners']['Setup Summary(Slow Corner)']['worst_slack_ns'],'board_programmed':False,'scope':physical['scope']})
 dump(ROOT/'docs/report_compare_fix_status.json',{'status':'PROMOTED83_PENDING_BOARD_TEST','main_project':'hardware/pds','candidate':str(src.relative_to(ROOT)),'configured_cpu_hz':83000000,'bitstream_sha256':sha(bit),'board_programmed':False,'diagnosis':'simulation/results/report_large_20261023/diagnosis.json'})
 print('PROMOTED',ps,rs,physical['estimated_fmax_mhz'],sha(bit),flush=True)
if __name__=='__main__':main()
