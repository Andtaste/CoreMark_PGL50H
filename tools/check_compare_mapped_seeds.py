"""Seed-only trials reuse a hash-bound mapped database; normal project remains rebuildable."""
from pathlib import Path
import argparse,concurrent.futures,json,re,shutil,subprocess
from verify_board_pnr import inspect,sha
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'simulation/results/report_compare_xor83_20261023_p9r1'
def run(pair):
 ps,rs=pair;p=BASE.with_name(f'report_compare_xor83_20261023_fast_p{ps}r{rs}');p.mkdir()
 for folder in ('source','ipcore','constraints','memory','device_map','synthesize'):shutil.copytree(BASE/folder,p/folder)
 for n in ('boot_interleaved.hex','generate_bitstream.tcl'):shutil.copyfile(BASE/n,p/n)
 s=(BASE/'new_core.pds').read_text();s=re.sub(r'\(_gci_state \(_integer \d+\)\)','(_gci_state (_integer 0))',s)
 for k,v in [('gplace_seed',ps),('groute_seed',rs)]:s=re.sub(r'\(_option '+k+r' \(_integer \d+\)\)',f'(_option {k} (_integer {v}))',s)
 assert 'input_place_db_file' not in s and 'enable_route_constraint_iterate' not in s
 (p/'new_core.pds').write_text(s)
 h={str(x.relative_to(p)):sha(x) for folder in ('source','ipcore','constraints','memory') for x in (p/folder).rglob('*') if x.is_file()}
 for n,v in h.items():assert sha(BASE/n)==v
 mapped=sha(p/'device_map/top_map.adf');assert mapped==sha(BASE/'device_map/top_map.adf')
 (p/'mapping_derivation.json').write_text(json.dumps({'parent':str(BASE.relative_to(ROOT)),'mapped_db_sha256':mapped,'input_sha256':h,'scope':'Only PnR seeds change. Full source rebuild is available through new_core.pds.'},indent=2))
 t='set root [file normalize [file dirname [info script]]]\ncd $root\nset_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\n'
 t+=f'pnr -input_db_file "$root/device_map/top_map.adf" -gplace_seed {ps} -groute_seed {rs} -max_ctrl_chain_length 4 -optimize_multi_corner_timing -fix_hold_violation\nreport_timing -max_path 30\n'
 (p/'route_seed.tcl').write_text(t)
 print('START mapped',ps,rs,flush=True)
 with (p/'native_build.log').open('wb') as f:subprocess.run(['E:/pango/PDS_2022.2-SP1-Lite/bin/pds_shell.exe','-f','route_seed.tcl'],cwd=p,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=3600)
 log=(p/'native_build.log').read_text(errors='replace');assert not re.search(r'^E:',log,re.M) and 'Report timing is finished successfully.' in log
 for n,v in h.items():assert sha(p/n)==v
 try:r=inspect(p,83)
 except AssertionError as e:
  t=(p/'report_timing/top.rtr').read_text();m=re.search(r'(\d+\.\d+) MHz\s+(\d+\.\d+) MHz',t)
  r={'status':'FAIL','reason':str(e),'estimated_fmax_mhz':float(m[2]),'sta_sha256':sha(p/'report_timing/top.rtr')}
 r.update(place_seed=ps,route_seed=rs,fanout_guide=64,project=str(p.relative_to(ROOT)),mapped_db_sha256=mapped)
 (p/'physical_result.json').write_text(json.dumps(r,indent=2)+'\n');print('DONE mapped',ps,rs,r['status'],r['estimated_fmax_mhz'],flush=True)
 return r
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--pairs',nargs='+',required=True);a=ap.parse_args();pairs=[tuple(map(int,s.split(','))) for s in a.pairs]
 assert all(len(p)==2 for p in pairs)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:rows=list(ex.map(run,pairs))
 suffix='_'.join(f'p{p}r{r}' for p,r in pairs);(BASE/f'mapped_seeds_{suffix}.json').write_text(json.dumps(rows,indent=2))
