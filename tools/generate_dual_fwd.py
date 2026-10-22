"""Isolated priority-masked forwarding and operand capture sharing."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_fwd_mask','dual_fwd_share'),required=True);a=ap.parse_args()
 src=ROOT/'simulation/results/load_bp_dual_if_parts';out=src.with_name('load_bp_'+a.variant);out.mkdir(exist_ok=True)
 meta=json.loads((src/'generation.json').read_text())
 for n,h in meta['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h,n;shutil.copyfile(p,out/p.name)
 for n,h in meta['ip_sha256'].items():assert sha(ROOT/n)==h,n
 shutil.copytree(src/'ipcore',out/'ipcore',dirs_exist_ok=True);shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 s=(out/'nc_operands.v').read_text()
 for op,wait in (('a','wa'),('b','wb')):
  old=f"  assign selected_v{op}[s]={wait}[s] ? (hit_f{op}[s] ? f_data : hit_f1{op}[s] ? f1_data : hit_m{op}[s] ? m_data : hit_w{op}[s] ? w_data : w1_data) : v{op}[s];"
  new=f"""  // Exclusive priority masks preserve F > F1 > M > W > W1.
  // The W1 fall-through also preserves the old value on unavailable cycles.
  wire use_{op}_f={wait}[s] && hit_f{op}[s];
  wire use_{op}_f1={wait}[s] && !hit_f{op}[s] && hit_f1{op}[s];
  wire use_{op}_m={wait}[s] && !(hit_f{op}[s] || hit_f1{op}[s]) && hit_m{op}[s];
  wire use_{op}_w={wait}[s] && !(hit_f{op}[s] || hit_f1{op}[s] || hit_m{op}[s]) && hit_w{op}[s];
  wire use_{op}_w1={wait}[s] && !(hit_f{op}[s] || hit_f1{op}[s] || hit_m{op}[s] || hit_w{op}[s]);
  assign selected_v{op}[s]=({{32{{!{wait}[s]}}}} & v{op}[s]) |
   ({{32{{use_{op}_f}}}} & f_data) | ({{32{{use_{op}_f1}}}} & f1_data) |
   ({{32{{use_{op}_m}}}} & m_data) | ({{32{{use_{op}_w}}}} & w_data) |
   ({{32{{use_{op}_w1}}}} & w1_data);"""
  assert old in s; s=s.replace(old,new)
  if a.variant=='dual_fwd_share':
   start=s.index(f'   if({wait}[i] && hit_f{op}[i])')
   end=s.index('\n',s.index(f'   else if({wait}[i] && hit_w1{op}[i])',start))
   s=s[:start]+f'   if({wait}[i] && available_{op}[i]) begin v{op}[i]<=selected_v{op}[i];{wait}[i]<=0;end'+s[end:]
 (out/'nc_operands.v').write_text(s)
 meta['override_sha256']['hardware\\pds\\source\\core\\nc_operands.v']=sha(out/'nc_operands.v')
 ips=[q for q in (out/'ipcore').rglob('*') if q.is_file() and q.suffix in ('.v','.idf')]
 meta['ip_sha256']={str(q.relative_to(ROOT)):sha(q) for q in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 meta.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope=a.variant+'; retained IF-parts parent, operands only, priority masked forwarding; same tags, depth, latency and capacity credit')
 (out/'generation.json').write_text(json.dumps(meta,indent=2)+'\n');print('GENERATED',a.variant)
if __name__=='__main__':main()
