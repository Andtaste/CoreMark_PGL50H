"""Constrain cells on measured frontend critical paths; preserve RTL and timing."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT/'simulation/results/continuous_clock83_shortmul_20261022'
 dest=ROOT/'simulation/results/continuous_clock83_shortmul_region_20261022'
 assert not dest.exists();meta=json.loads((src/'prepared.json').read_text())
 active=ROOT/'docs/active_optimization_baseline.json';m=json.loads(active.read_text())
 assert json.loads((src/'parent_baseline.json').read_text())==m
 for n,h in meta['input_sha256'].items():assert sha(src/n)==h,n
 report=ROOT/m['project_directory']/'report_timing/top.rtr';cells=set()
 for block in report.read_text().split('Startpoint  : ')[1:11]:
  assert 'max (slow corner)' in block
  data=block.split('Data arrival time',1)[0]
  for line in data.splitlines():
   match=re.search(r'\s(soc/cpu/[^\s]+)\s*$',line)
   if match and (' td ' in line or ' tco ' in line or '/CLK' in line or 'Endpoint ' in line):
    cells.add(match[1].rsplit('/',1)[0])
 assert 10<=len(cells)<=200,len(cells)
 exported=ROOT/'simulation/results/autonomous_20261022/physical_followup/placed_primitives.pcf'
 prefixes={s.rsplit('/',1)[0] for s in cells}
 cells={s for s in re.findall(r'def_inst_site \{([^}]+)\}',exported.read_text()) if s.rsplit('/',1)[0] in prefixes}
 assert 50<=len(cells)<=250,len(cells)
 mapping=json.loads((exported.parent/'critical_mapped_cells.json').read_text())
 assert mapping['reference_sta_sha256']==sha(report) and mapping['constraint_export_sha256']==sha(exported)
 cells-=set(mapping['excluded_postpacking_aliases'])
 assert cells==set(mapping['cells'])
 dest.mkdir()
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder)
 for p in (dest/'ipcore').rglob('*'):
  if p.is_file() and p.suffix in ('.v','.idf','.vhdl'):p.write_bytes(p.read_bytes().replace(src.as_posix().encode(),dest.as_posix().encode()))
 for folder in ('source','ipcore','memory'):
  for p in (dest/folder).rglob('*'):
   if p.is_file():assert p.read_bytes().replace(dest.as_posix().encode(),src.as_posix().encode())==(src/p.relative_to(dest)).read_bytes()
 constraint='\n# Measured frontend critical cells only; no timing exceptions.\ndef_region frontend_critical 83 111 34 62\n'
 constraint+=''.join('def_inst_region {'+cell+'} frontend_critical\n' for cell in sorted(cells))
 (dest/'constraints/frontend_region.pcf.fragment').write_text(constraint)
 s=re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',(src/'new_core.pds').read_text());(dest/'new_core.pds').write_text(s)
 shutil.copyfile(active,dest/'parent_baseline.json')
 meta.update(strategy='critical_region',changed_option={},place_seed=3,route_seed=1,scope='Same83MHz RTL/IP/software. Only spatial constraints on cells measured on accepted82MHz frontend critical paths; strict instance checks, no false/multicycle paths.',constraint_entry='Append fragment to generated PCF after dev_map and before PNR in one full Tcl flow; original FDC unchanged.',region={'bounds':[83,111,34,62],'cells':sorted(cells)},reference_sta_sha256=sha(report),constraint_export_sha256=sha(exported))
 meta['input_sha256']={str(p.relative_to(dest)):sha(p) for folder in ('source','ipcore','constraints','memory') for p in (dest/folder).rglob('*') if p.is_file()}
 (dest/'prepared.json').write_text(json.dumps(meta,indent=2)+'\n')
 print('PREPARED critical region',len(cells),'cells',flush=True)
 tcl=dest/'new_core.tcl';tcl.write_text('set root [file normalize [file dirname [info script]]]\nset_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\nforeach directory {core perips sys_bus top source} {\n foreach src [lsort [glob -directory "$root/source/$directory" *.v]] {add_design $src}\n}\nforeach ip {pll ram1_tdp ram2_tdp} {add_design "$root/ipcore/$ip/$ip.idf"}\nadd_constraint "$root/constraints/board.fdc"\ncompile -top_module top\nsynthesize -ads -selected_syn_tool_opt 2\ndev_map\nset fragment [open "$root/constraints/frontend_region.pcf.fragment" r]\nset physical [open "$root/device_map/top.pcf" a]\nputs $physical [read $fragment]\nclose $fragment\nclose $physical\nfile copy -force "$root/device_map/top.pcf" "$root/effective_placement_constraints.pcf"\npnr -gplace_seed 3 -groute_seed 1 -max_ctrl_chain_length 4 -optimize_multi_corner_timing -fix_hold_violation -fix_hold_violation_in_route TRUE\nreport_timing -max_path 30 -nworst 1\n')
 with (dest/'native_build.log').open('wb') as f:
  subprocess.run(['E:/pango/PDS_2022.2-SP1-Lite/bin/pds_shell.exe','-f',str(tcl)],cwd=dest,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=3600)
if __name__=='__main__':main()
