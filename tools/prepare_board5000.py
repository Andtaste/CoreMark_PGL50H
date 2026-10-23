"""Prepare a separate board image without altering the accepted fixed-10 PDS project."""
from pathlib import Path
import hashlib,json,shutil,subprocess,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 base=ROOT/'hardware/pds';dest=ROOT/'hardware/pds_board5000';out=ROOT/'docs/board5000_20261022'
 assert not dest.exists(),'Board project already exists; do not overwrite a built result'
 build=json.loads((ROOT/'sw/build/coremark_performance_5000/build.json').read_text())
 assert build['iterations']==5000 and build['cpu_hz']==82000000 and not build['validation']
 assert sha(ROOT/'sw/build/boot.hex')==build['hex_sha256']
 accepted=json.loads((ROOT/'docs/accepted_dual_baseline.json').read_text(encoding='utf-8'))
 for folder in ('source','constraints','ipcore'):shutil.copytree(base/folder,dest/folder)
 (dest/'memory').mkdir();shutil.copyfile(ROOT/'sw/build/boot.hex',dest/'memory/boot.hex')
 words=[int(x,16) for x in (dest/'memory/boot.hex').read_text().split()];assert len(words)==16384
 lines=[]
 for i in range(0,len(words),2):
  data=words[i].to_bytes(4,'little')+words[i+1].to_bytes(4,'little')
  encoded=bytes(data[j] for j in (0,4,1,5,2,6,3,7))
  assert bytes(encoded[j] for j in (0,2,4,6,1,3,5,7))==data
  lines.append(encoded[::-1].hex())
 image=dest/'memory/boot_interleaved.hex';image.write_text('\n'.join(lines)+'\n')
 ram=dest/'ipcore/ram1_tdp';idf=ram/'ram1_tdp.idf';tree=ET.parse(idf)
 for p in tree.findall('.//param'):
  if p.findtext('name')=='INIT_FILE':p.find('value').text=image.as_posix()
 tree.write(idf,encoding='utf-8',xml_declaration=True)
 with (out/'ram1_generate.log').open('wb') as stream:
  result=subprocess.run(['E:/pango/PDS_2022.2-SP1-Lite/bin/ip_generate.exe','-i',str(idf),'-disable-syn'],cwd=ram,stdout=stream,stderr=subprocess.STDOUT,timeout=180)
 assert result.returncode==0,'RAM IP generation failed'
 rtl={str(p.relative_to(ROOT)):sha(p) for p in (dest/'source').rglob('*.v')}
 assert len(rtl)==17
 for p in (dest/'source').rglob('*.v'):assert p.read_bytes()==(base/p.relative_to(dest)).read_bytes()
 prefix='''set root [file normalize [file dirname [info script]]]
cd $root
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
 (dest/'new_core.tcl').write_text(prefix+'pnr -gplace_seed 22 -gplace_times 1 -saved_outcome 1 -parallel 1 -groute_seed 4 -groute_times 1 -max_ctrl_chain_length 4 -optimize_multi_corner_timing -fix_hold_violation -fix_hold_violation_in_route TRUE\nreport_timing -max_path 30 -nworst 1\n')
 (dest/'generate_bitstream.tcl').write_text('set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484\ngen_bit_stream\n')
 record=dict(status='PREPARED_REBUILD_AND_SIMULATION_REQUIRED',iterations=5000,configured_cpu_hz=82000000,uart_baud=115200,uart_divisor=712,accepted_descriptor_sha256=sha(ROOT/'docs/accepted_dual_baseline.json'),cpu_rtl_unchanged=True,rtl_sha256=rtl,input_sha256={str(p.relative_to(ROOT)):sha(p) for folder in ('source','constraints','ipcore','memory') for p in (dest/folder).rglob('*') if p.is_file() and p.suffix in ('.v','.idf','.fdc','.hex')},firmware_manifest_sha256=sha(ROOT/'sw/build/coremark_performance_5000/build.json'),source_project='hardware/pds_board5000/new_core.pds',historical_fixed10_project='hardware/pds/new_core.pds',note='Fresh native synthesis/mapping required for changed BRAM INIT. No reuse of the fixed-10 canonical mapping or its timing claim.')
 (out/'prepared.json').write_text(json.dumps(record,indent=2)+'\n');print('PREPARED board5000; 17 RTL byte-identical; fresh 82MHz native build required')
if __name__=='__main__':main()
