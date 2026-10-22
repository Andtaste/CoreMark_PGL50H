"""Read routed pointer instances, their measured fanouts and path timings."""
from pathlib import Path
import argparse,collections,hashlib,json,re,subprocess
from archive_dual_issue import paths
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_if_parts','dual_fan_guide','dual_fan_banks'),required=True);ap.add_argument('--reuse-reports',action='store_true');a=ap.parse_args()
 source=ROOT/('simulation/results/load_bp_'+a.variant);adf=source/'pds/place_route/top_pnr.adf';netlist=source/'pds/place_route/top_pnr.netlist'
 dest=ROOT/'simulation/results/dual_fan_paths'/a.variant;dest.mkdir(parents=True,exist_ok=True)
 guard={p:sha(p) for p in (adf,source/'pds/report_timing/top.rtr',ROOT/'docs/accepted_baseline.json',ROOT/'hardware/pds/report_timing/top.rtr')}
 commands=['set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484']
 for k in ('rd','wr'):
  commands+=['report_timing -force_to_run -input_db_file {'+adf.as_posix()+'} -max_path 100 -nworst 1 -from {soc/cpu/memory_queue/*'+k+'*/CLK}',
   'file copy -force report_timing/top.rtr '+k+'.rtr']
 tcl=dest/'target.tcl';prior=None
 if a.reuse_reports:
  prior=json.loads((dest/'result.json').read_text())
  for q in (adf,netlist,tcl):assert sha(q)==prior['input_sha256'][str(q.relative_to(ROOT))],q
  assert tcl.read_text()=='\n'.join(commands)+'\n'
 else:
  tcl.write_text('\n'.join(commands)+'\n')
  with (dest/'build.log').open('wb') as f:p=subprocess.run([r'E:\pango\PDS_2022.2-SP1-Lite\bin\pds_shell.exe','-f',str(tcl)],cwd=dest,stdout=f,stderr=subprocess.STDOUT,timeout=240)
  assert p.returncode==0,(dest/'build.log').read_text(errors='replace')[-3000:]
 insts=re.findall(r'\nInst\n([^;\n]+);([^\n]+)\n(.*?)(?=\n\n|\Z)',netlist.read_text(),re.S)
 pointers=[dict(name=n,type=t) for n,t,b in insts if '/memory_queue/' in n and re.search(r'(?:/|\.)(?:rd|wr)(?:\[|_)',n) and '\nCLK;1' in b]
 assert pointers,pointers
 ram=collections.Counter()
 for n,t,b in insts:
  if not t.startswith('gopRAM'):continue
  key='rf' if '/rf/' in n else 'memory_queue' if '/memory_queue/' in n else 'btb' if '/predictor.btb' in n else 'fetch' if '/fetch/instructions' in n else 'other';ram[key]+=1
 timing={};fanout={}
 for k in ('rd','wr'):
  text=(dest/(k+'.rtr')).read_text();timing[k]=paths(dest/(k+'.rtr'));assert timing[k],k
  for part in text.split('Startpoint  : ')[1:]:
   if 'tco' not in part or 'Data arrival time' not in part:continue
   m=re.search(r'\btco\b.*?net \(fanout=(\d+)\)',part,re.S)
   if m:fanout[part.splitlines()[0].strip()]=int(m[1])
 for q,h in guard.items():assert sha(q)==h,q
 x=dict(status='PASS',variant=a.variant,pointer_instances=pointers,pointer_instance_count=len(pointers),observed_pointer_fanout=fanout,
  fanout_scope='First data net after each pointer clock-to-Q in targeted reports; a pointer absent from selected paths has no claimed fanout.',
  distributed_ram=dict(ram),targeted_paths=timing,input_sha256={str(q.relative_to(ROOT)):sha(q) for q in (adf,netlist,tcl,dest/'rd.rtr',dest/'wr.rtr',Path(__file__).resolve())},
  reports_reused=a.reuse_reports,previous_parser_sha256=(prior['input_sha256'].get(str(Path(__file__).resolve().relative_to(ROOT))) if prior else None))
 (dest/'result.json').write_text(json.dumps(x,indent=2)+'\n')
 print(json.dumps(dict(variant=a.variant,pointer_instances=len(pointers),observed_fanout=fanout,distributed_ram=dict(ram),worst={k:v[0] for k,v in timing.items()}),indent=2))
if __name__=='__main__':main()
