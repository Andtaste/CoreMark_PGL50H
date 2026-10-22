"""Isolated fanout guidance or four-bank FIFO pointer replication."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_fan_guide','dual_fan_banks'),required=True);a=ap.parse_args()
 src=ROOT/'simulation/results/load_bp_dual_if_parts';out=src.with_name('load_bp_'+a.variant);out.mkdir(exist_ok=True)
 meta=json.loads((src/'generation.json').read_text())
 for n,h in meta['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h,n;shutil.copyfile(p,out/p.name)
 for n,h in meta['ip_sha256'].items():assert sha(ROOT/n)==h,n
 shutil.copytree(src/'ipcore',out/'ipcore',dirs_exist_ok=True);shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 if a.variant=='dual_fan_guide':
  s=(ROOT/'hardware/pds/source/core/nc_fifo.v').read_text()
  s=s.replace('reg[PTR-1:0] rd,wr;','reg[PTR-1:0] rd,wr /* synthesis syn_maxfan=64 */;')
  s=s.replace('wire push=in_valid && in_ready;','wire push /* synthesis syn_maxfan=64 */;assign push=in_valid && in_ready;')
 else:
  s='''// Four width banks with explicit identical pointer copies. Occupancy
// remains global and registered: no output-ready to input-credit path.
module nc_fifo #(parameter WIDTH=32,parameter DEPTH=2)(
 input wire clk,rst_n,clear,
 input wire in_valid,output wire in_ready,input wire[WIDTH-1:0] in_data,
 output wire out_valid,input wire out_ready,output wire[WIDTH-1:0] out_data
);
 localparam PTR=$clog2(DEPTH),CNT=$clog2(DEPTH+1),BANKS=WIDTH>=4 ? 4 : 1;
 reg[CNT-1:0] count;
 assign in_ready=count!=DEPTH;
 assign out_valid=count!=0;
 wire push /* synthesis syn_maxfan=64 */;assign push=in_valid && in_ready;
 wire pop=out_valid && out_ready;
 genvar b;
 generate for(b=0;b<BANKS;b=b+1) begin:bank
  localparam LO=b*WIDTH/BANKS,BW=(b+1)*WIDTH/BANKS-LO;
  reg[BW-1:0] data[0:DEPTH-1] /* synthesis syn_ramstyle="lut_ram" */;
  reg[PTR-1:0] rd,wr /* synthesis syn_preserve=1 */;
  assign out_data[LO+:BW]=data[rd];
  always @(posedge clk) if(push) data[wr]<=in_data[LO+:BW];
  always @(posedge clk or negedge rst_n) begin
   if(!rst_n) begin rd<=0;wr<=0;end
   else if(clear) begin rd<=0;wr<=0;end
   else begin if(push) wr<=wr+1'b1;if(pop) rd<=rd+1'b1;end
  end
 end endgenerate
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) count<=0;
  else if(clear) count<=0;
  else case({push,pop}) 2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:;endcase
 end
endmodule
'''
 (out/'nc_fifo.v').write_text(s);meta['override_sha256']['hardware\\pds\\source\\core\\nc_fifo.v']=sha(out/'nc_fifo.v')
 ips=[q for q in (out/'ipcore').rglob('*') if q.is_file() and q.suffix in ('.v','.idf')]
 meta['ip_sha256']={str(q.relative_to(ROOT)):sha(q) for q in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 meta.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),scope=a.variant+'; retained IF-parts parent, FIFO only, same depth/latency/capacity credit')
 (out/'generation.json').write_text(json.dumps(meta,indent=2)+'\n');print('GENERATED',a.variant)
if __name__=='__main__':main()
