"""Snapshot the actual 80MHz project and prepare a genuine 82MHz seed sweep."""
from pathlib import Path
from datetime import datetime
import hashlib,json,shutil,subprocess,xml.etree.ElementTree as ET,zipfile,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 src=ROOT/'hardware/pds';dest=ROOT/'hardware/pds82_seed_sweep';out=ROOT/'docs/clock82_multiseed_20261022';assert not (out/'prepared.json').exists()
 accepted=ROOT/'docs/accepted_dual_baseline.json';a=json.loads(accepted.read_text(encoding='utf-8'));assert a['variant']=='dual_boundary_next_pairbranch'
 original=[p for folder in ('source','ipcore','constraints','memory') for p in (src/folder).rglob('*') if p.is_file()]
 original +=[p for p in src.iterdir() if p.is_file() and p.suffix in ('.tcl','.pds','.json','.csv')]
 original +=[src/n for n in ('report_timing/top.rtr','place_route/top_pnr.adf','synthesize/top_syn.vm','synthesize/top.snr','device_map/top.dmr','place_route/multiseed_result.csv') if (src/n).exists()]
 for folder in ('place_route/seed_8','report_timing'):
  original +=[p for p in (src/folder).glob('*') if p.is_file() and p.suffix in ('.rtr','.txt','.log','.adf')]
 original=sorted(set(original));out.mkdir(exist_ok=True);dest.mkdir(exist_ok=True)
 before={str(p.relative_to(src)):sha(p) for p in original}
 with zipfile.ZipFile(out/'before80_snapshot.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in original:z.write(p,p.relative_to(src).as_posix())
 with zipfile.ZipFile(out/'before80_snapshot.zip') as z:
  for n,h in before.items():assert hashlib.sha256(z.read(n.replace('\\','/'))).hexdigest()==h,n
 save(out/'before80_manifest.json',before)
 for folder in ('source','ipcore','constraints','memory'):shutil.copytree(src/folder,dest/folder,dirs_exist_ok=True)
 top=dest/'source/source/top.v';data=top.read_bytes();assert data.count(b'CLOCK_HZ(80000000)')==1;top.write_bytes(data.replace(b'CLOCK_HZ(80000000)',b'CLOCK_HZ(82000000)'))
 old_image=(src/'memory/boot_interleaved.hex').as_posix().encode();new_image=(dest/'memory/boot_interleaved.hex').as_posix().encode()
 for p in (dest/'ipcore').rglob('*'):
  if p.is_file() and p.suffix in ('.v','.idf','.vhdl'):p.write_bytes(p.read_bytes().replace(old_image,new_image))
 pll=dest/'ipcore/pll';idf=pll/'pll.idf';tree=ET.parse(idf)
 # Actual hardware ratio: 50/5*82/10=82MHz; 820MHz VCO.
 values={'STATIC_RATIOI':'5','STATIC_RATIOF':'82','STATIC_RATIO0':'10','STATIC_DUTY0':'10','STATIC_DUTYF':'82','CLKOUT0_REQ_FREQ':'82.0000'}
 changed=[]
 for item in tree.findall('./param_list/param'):
  n=item.findtext('name')
  for k,v in values.items():
   if n in (k+'_basicPage',k+'_advancedPage'):item.find('value').text=v;changed.append(n)
 assert len(changed)>=10 and all(k+'_'+page in changed for k in ('STATIC_RATIOI','STATIC_RATIOF','STATIC_RATIO0') for page in ('basicPage','advancedPage')),changed
 tree.write(idf,encoding='utf-8',xml_declaration=True)
 with (pll/'clock82_generate.log').open('wb') as f:x=subprocess.run([r'E:\pango\PDS_2022.2-SP1-Lite\bin\ip_generate.exe','-i',str(idf),'-disable-syn'],cwd=pll,stdout=f,stderr=subprocess.STDOUT,timeout=180)
 assert x.returncode==0,(pll/'clock82_generate.log').read_text(errors='replace')[-3000:]
 text=(pll/'pll.v').read_text()
 for k,v in (('STATIC_RATIOI',5),('STATIC_RATIOF',82),('STATIC_RATIO0',10)):assert re.search(r'\b'+k+r'\s*=\s*'+str(v)+r';',text),k
 # Explicit clocks, unmodified board input constraints and original PnR options.
 prefix='''set root [file normalize [file dirname [info script]]]
set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484
foreach directory {core perips sys_bus top source} {
 foreach src [lsort [glob -directory "$root/source/$directory" *.v]] {add_design $src}
}
foreach ip {pll ram1_tdp ram2_tdp} {add_design "$root/ipcore/$ip/$ip.idf"}
add_constraint "$root/constraints/board.fdc"
compile -top_module top
synthesize -ads -selected_syn_tool_opt 2
dev_map
'''
 command='pnr -gplace_seed 0 -gplace_times 10 -seed_step 1 -saved_outcome 10 -parallel 3 -max_ctrl_chain_length 4 -optimize_multi_corner_timing -fix_hold_violation -fix_hold_violation_in_route TRUE'
 (dest/'new_core.tcl').write_text(prefix+command+'\nreport_timing -max_path 30 -nworst 1\n',encoding='utf-8')
 changes={}
 for p in (dest/'source').rglob('*.v'):
  n=str(p.relative_to(dest));h=sha(p);old=sha(src/p.relative_to(dest))
  if h!=old:changes[n]=dict(before=old,after=h)
 assert list(changes)==['source\\source\\top.v'],changes
 record=dict(status='PREPARED',created_at=datetime.now().astimezone().isoformat(),user_instruction='频率改到82，布局多试试几个seed，看看能不能收敛',variant=a['variant'],accepted_descriptor_sha256=sha(accepted),requested_clock_hz=82000000,requested_period_ns=1000/82,uart_divisor=712,pll_ratio=dict(input_mhz=50,divide_input=5,multiply_feedback=82,divide_output=10,vco_mhz=820),seeds=list(range(10)),parallel=3,pnr_command=command,trial_directory=str(dest.relative_to(ROOT)),before80_snapshot_sha256=sha(out/'before80_snapshot.zip'),before80_source_sha256=before,changed_cpu_rtl=changes,input_sha256={str(p.relative_to(ROOT)):sha(p) for folder in ('source','ipcore','constraints','memory') for p in (dest/folder).rglob('*') if p.is_file() and p.suffix in ('.v','.idf','.fdc','.hex')},note='Core pipeline unchanged; only actual PLL and top CLOCK_HZ change. Native PDS place seeds 0..9, same route options and board constraints; full setup/hold gate, no timing exceptions. Original software retains diagnostic 75MHz printed metadata.')
 record['input_sha256'][str((dest/'new_core.tcl').relative_to(ROOT))]=sha(dest/'new_core.tcl');record['input_sha256']['tools/prepare_clock82_sweep.py']=sha(Path(__file__))
 save(out/'prepared.json',record);print('PREPARED real PLL82, UART712, 10 seeds / 3 parallel; complete 80MHz input + routed snapshot saved')
if __name__=='__main__':main()
