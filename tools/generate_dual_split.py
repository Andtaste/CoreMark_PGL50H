"""Admission-time split: keep an unready younger instruction at the sliding head."""
from pathlib import Path
import argparse,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_split_ready','dual_split_slow'),required=True);a=ap.parse_args()
 src=ROOT/'simulation/results/load_bp_dual_joint_fix';out=src.with_name('load_bp_'+a.variant);assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_core.v';s=p.read_text();needle='  dep_c=id_pair_flags[5] && |(match_c|match_c1);dep_d=id_pair_flags[6] && |(match_d|match_d1);';assert s.count(needle)==1
 if a.variant=='dual_split_ready':
  terms=[]
  for op in 'cd':
   hits=[f'(f_valid && tag_{op}=={{f_tag,1\'b0}})',f'(f1_valid && tag_{op}=={{f1_tag,1\'b1}})',f'(m_valid && tag_{op}=={{m_tag,m_lane}})',f'(commit && w_wr && w_rd!=0 && tag_{op}=={{w_tag,1\'b0}})',f'(commit1 && w1_rd!=0 && tag_{op}=={{w_tag,1\'b1}})']
   terms.append(f'(dep_{op} && !('+ ' || '.join(hits)+'))')
  logic=' || '.join(terms)
 else:
  needle2=' reg barrier;reg[7:0] live;';assert s.count(needle2)==1;s=s.replace(needle2,' reg[7:0] slow_main,slow_side;\n'+needle2)
  needle2=' wire ex_credit,ex_valid,ex_pop,ex_occupied;';assert s.count(needle2)==1;s=s.replace(needle2,' always @(posedge clk) if(issue) begin slow_main[tail]<=id_kind==4 || id_kind==6;slow_side[tail]<=id_side_kind==6;end\n'+needle2)
  logic="(dep_c && (tag_c[0] ? slow_side[tag_c[3:1]] : slow_main[tag_c[3:1]])) || (dep_d && (tag_d[0] ? slow_side[tag_d[3:1]] : slow_main[tag_d[3:1]]))"
 s=s.replace(needle,needle+'\n  // Split at ID before allocating an atomic group; keep younger word in IF.\n  second_dep='+logic+';')
 s=s.replace('// Lane1 never waits: any live source producer or intra-pair RAW splits', '// Side admission follows this experiment policy; intra-pair RAW splits')
 p.write_text(s);g['override_sha256']['hardware\\pds\\source\\core\\nc_core.v']=sha(p)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope=a.variant+'; isolate ID splitting from combined fix; side source unready splits (ready) or load/MUL/DIV producer splits (slow); ordinary ALU dependencies may wait in slow; all other features and sources identical; no EX replay or group retag; no adoption')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',a.variant)
if __name__=='__main__':main()
