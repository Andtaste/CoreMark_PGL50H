"""Adapt the frozen old CPU's atomic two-request contract to common RAM service."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
 base=ROOT/'tools/compare_dual_boundary_old.py';s=base.read_text().replace("('old','fifo','slot','early')","('old','fifo','slot','early','read')")
 needle="  cp='''tinyriscv_core cpu";s=s.replace(needle,"  p=old/'source/utils/gen_dff.v';assert sha(p)==hashes['utils/gen_dff.v'];q=snap/p.name;shutil.copyfile(p,q);corefiles.append(q);inputs +=[p,q]\n"+needle)
 s=s.replace('.dbus_pair_o());','.dbus_pair_o(pair));').replace(' assign sv=0;',' assign pair=0;assign sv=0;').replace('sv,sr,sov,sor,swrite,tx;','sv,sr,sov,sor,swrite,tx,pair;').replace("a.target=='early' else", "a.target in ('early','read') else")
 needle=" tb=out/'common_tb.v';"
 code=''' # The old CPU advances a dual memory group only if both requests accept
 # together. Its original bus implements this atomic contract. The common
 # adapter adds the same contract explicitly; independent new-CPU pairs use
 # pair=0. Distinct 32-bit words have defined masked behavior in this model.
 original_bus=bus;bs=bus.read_text().replace('input wire iv,output wire ir,','input wire pair,input wire iv,output wire ir,')
 bs=bs.replace('assign dr=rst_n && (!dpending || dor) && !primary_hold && !(dwrite && uart_addr && !uart_ready);','wire primary_base=rst_n && (!dpending || dor) && !primary_hold && !(dwrite && uart_addr && !uart_ready);\\n wire pair_alias=da[31:2]==sa[31:2] && (dwrite || swrite);\\n assign dr=primary_base && (!pair || (secondary_base && !pair_alias));')
 bs=bs.replace('da[31:3]==sa[31:3]','da[31:2]==sa[31:2]')
 bs=bs.replace('assign sr=rst_n && (sb0 || sb1) && (!spending || sor) && !secondary_hold &&\\n                       (SECOND_PORT ? !local_collision : !dv);','wire secondary_base=rst_n && (sb0 || sb1) && (!spending || sor) && !secondary_hold;\\n assign sr=secondary_base && (!pair || (primary_base && !pair_alias)) && (pair || (SECOND_PORT ? !local_collision : !dv));')
 bus=out/'nc_local_bus_common.v';bus.write_text(bs);inputs +=[original_bus]
'''
 assert s.count(needle)==1;s=s.replace(needle,code+needle).replace('bus(.clk(clk),.rst_n(rst_n),.iv(iv)','bus(.clk(clk),.rst_n(rst_n),.pair(pair),.iv(iv)')
 ns={'__file__':str(base),'__name__':'common_v3'};exec(compile(s,str(base),'exec'),ns);ns['main']()
 v=sys.argv[sys.argv.index('--target')+1];p=ROOT/('simulation/results/dual_boundary_common/'+v+'/result.json');x=json.loads(p.read_text());x['scope']='Same fixed firmware and common behavioral RAM/peripheral service; frozen Round50 CPU uses explicit atomic pair contract; distinct 32-bit-word masked A/B behavior defined in model only; not original SoC/IP timing comparison';x['input_sha256'][str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(x,indent=2)+'\n')
if __name__=='__main__':main()
