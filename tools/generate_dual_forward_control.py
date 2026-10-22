"""Move queue-head choice into forwarding control, preserving all priorities."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_boundary_headmux',),required=True);a=ap.parse_args()
 accepted=ROOT/'docs/accepted_dual_baseline.json';d=json.loads(accepted.read_text());assert d['variant']=='dual_boundary_storewrite'
 src=ROOT/d['source_directory'];out=src.with_name('load_bp_'+a.variant);assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_operands.v';s=p.read_text();s=rep(s,'selected_c[rd],selected_d[rd]','head_c,head_d')
 declarations=''.join(f' wire[1:0] headmask_{op}_{source};\n' for op in 'abcd' for source in ('f','f1','m','w','w1'))
 s=rep(s,' genvar s;',declarations+' genvar s;')
 assignments=''.join(f'  assign headmask_{op}_{source}[s]=use_{op}_{source};\n' for op in 'abcd' for source in ('f','f1','m','w','w1'))
 s=rep(s,' end endgenerate',assignments+' end endgenerate')
 body=''' // Distribute the physical-head choice over the source masks. Broadcast
 // data now goes through one shared OR plane, rather than a per-slot
 // 32-bit source mux followed by a 32-bit queue-head mux. The original
 // per-slot selectors remain for stalled-operand capture. No cycle change.
'''
 for op,wait,storage in (('a','wa','va'),('b','wb','vb'),('c','wc','side'),('d','wd','side')):
  stored=lambda i: f'{storage}[{i}]'+('[135:104]' if op=='c' else '[103:72]' if op=='d' else '')
  body+=f' wire[31:0] head_{op}=({{32{{!rd && !{wait}[0]}}}} & {stored(0)}) |\n  ({{32{{rd && !{wait}[1]}}}} & {stored(1)})'
  for source in ('f','f1','m','w','w1'):
   body+=f' |\n  ({{32{{(!rd && headmask_{op}_{source}[0]) || (rd && headmask_{op}_{source}[1])}}}} & {source}_data)'
  body+=';\n'
 body+=' wire[31:0] a=head_a,b=head_b;'
 s=rep(s,' wire[31:0] a=selected_va[rd],b=selected_vb[rd];',body);p.write_text(s)
 for n in g['override_sha256']:g['override_sha256'][n]=sha(out/Path(n).name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')]
 g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),accepted_dual_sha256=sha(accepted),scope='Only operand output mux factoring: head choice distributed into original exclusive source masks; original captures, availability, insertion, priorities and invalid-cycle values preserved; no new registers or cycle; not adopted')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',a.variant)
if __name__=='__main__':main()
