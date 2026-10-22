"""Rebuild EX/MEM ownership around one MEM slot and an empty-queue handoff."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_boundary_slot','dual_boundary_early'),required=True);a=ap.parse_args()
 src=ROOT/'simulation/results/load_bp_dual_legacy_fifo';out=src.with_name('load_bp_'+a.variant);assert not out.exists();out.mkdir()
 g=json.loads((src/'generation.json').read_text());accepted=ROOT/'docs/accepted_dual_baseline.json';assert sha(accepted)=='acc8a0f8be1dc90d67e6cda8d18fc000911cc4b25a8021ab0f7b17ec244abb01'
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 p=out/'nc_core.v';s=p.read_text();s=rep(s,'wire[183:0] compact_packet;wire[64:0] compact_side,memory_side;', '''wire[183:0] compact_packet;wire[64:0] compact_side,memory_side;
 wire queued_valid,queue_credit;wire[248:0] queued_packet;
 wire[248:0] incoming_packet={side_result,ex_tag,execute_packet[276:181],queue_value,queue_aux,execute_packet[20:0]};
 // Input credit is still registered occupancy. Empty queue hands EX to the
 // MEM slot on the same edge; blocked instructions enter the existing FIFO.
 assign mem_credit=queue_credit;
 assign mem_valid=queued_valid || execute_valid;
 assign {compact_side,compact_packet}=queued_valid ? queued_packet : incoming_packet;
 wire direct_take=!queued_valid && execute_valid && memory_ready;''')
 s=rep(s,'''  .in_valid(execute_valid),.in_ready(mem_credit),
  .in_data({side_result,ex_tag,execute_packet[276:181],queue_value,queue_aux,execute_packet[20:0]}),
  .out_valid(mem_valid),.out_ready(memory_ready),.out_data({compact_side,compact_packet}));''','''  .in_valid(execute_valid && !direct_take),.in_ready(queue_credit),
  .in_data(incoming_packet),
  .out_valid(queued_valid),.out_ready(memory_ready),.out_data(queued_packet));''')
 s=rep(s,' nc_memory memory(', ' nc_memory #(.EARLY_REQUEST('+str(int(a.variant.endswith('_early')))+')) memory(');p.write_text(s)
 old=(src/'nc_memory.v').read_text();shape=old[old.index(' reg load_word,'):old.index(' always @(posedge clk) begin')]
 text='''// Uniform MEM register owns every group. The spill FIFO is optional when empty.
// Local requests may launch at the EX/MEM ownership edge; MMIO starts in MEM.
// Bus response and load formatting terminate at existing registered WB only.
module nc_memory #(parameter EARLY_REQUEST=0)(input wire clk,rst_n,kill,input wire valid,output wire ready,
 input wire[64:0] side_packet,output wire[64:0] wb_side,
 input wire[279:0] packet,output wire wb_valid,output wire[279:0] wb_packet,
 output wire[2:0] mul_tag,input wire mul_ready,input wire[31:0] mul_data,output wire mul_consume,
 output wire req_valid,input wire req_ready,output wire[31:0] req_addr,req_data,
 output wire[3:0] req_mask,output wire req_write,
 input wire rsp_valid,output wire rsp_ready,input wire[31:0] rsp_data,input wire rsp_error);
 localparam IDLE=2'd0,MEMORY=2'd1,BUFFERED=2'd2;
 reg slot_valid,sent;reg[279:0] held;reg[64:0] held_side;
 wire[31:0] pc,insn,next_pc,result,address,store_data,tval,csr_data;
 wire[4:0] cause,rd;wire[2:0] f3,tag;wire[3:0] kind;wire wr,exception,csr_we,serial;
 assign {tag,pc,insn,next_pc,result,address,store_data,tval,csr_data,cause,rd,f3,kind,wr,exception,csr_we,serial}=held;
 wire memory_access=!exception && (kind==4 || kind==5);
 wire primary_multiply=!exception && kind==6 && !f3[2];
 wire secondary_multiply=!exception && held_side[64] && !held_side[38] && held_side[37] && !held_side[34] && held_side[57];
 wire multiply_access=primary_multiply || secondary_multiply;
 wire memory_pending=slot_valid && memory_access,buffered=slot_valid && !memory_access;
 wire[1:0] state=!slot_valid ? IDLE : memory_access ? MEMORY : BUFFERED;
 wire response=memory_pending && sent && rsp_valid;
 wire response_error=response && rsp_error;
 wire complete=slot_valid && (!memory_access || response) && (!multiply_access || mul_ready);
 wire can_accept=!kill && (!slot_valid || (complete && !exception && !response_error));
 assign ready=can_accept;
 wire start=valid && ready;
 wire input_memory=!packet[2] && (packet[7:4]==4 || packet[7:4]==5);
 wire[31:0] input_address=packet[148:117];
 wire input_local=input_address<32'h00010000 || (input_address>=32'h10000000 && input_address<32'h10008000);
 wire old_request=memory_pending && !sent;
 wire early_request=EARLY_REQUEST && can_accept && valid && input_memory && input_local;
 // Ownership, rather than request valid, selects payload. If an early
 // request is blocked, its identical payload moves into held on this edge.
 wire use_input=!old_request;
 wire[31:0] request_address=use_input ? input_address : address;
 wire[31:0] request_data=use_input ? packet[116:85] : store_data;
 wire[2:0] request_f3=use_input ? packet[10:8] : f3;
 assign req_valid=!kill && (old_request || early_request);
 assign req_addr=request_address;
 assign req_data=request_data << {request_address[1:0],3'b0};
 assign req_mask=request_f3[1:0]==0 ? (4'b1<<request_address[1:0]) : request_f3[1:0]==1 ? (4'b11<<request_address[1:0]) : 4'b1111;
 assign req_write=use_input ? packet[7:4]==5 : kind==5;
 assign rsp_ready=memory_pending && sent && !kill;
 assign mul_tag=tag;assign mul_consume=wb_valid && multiply_access;
 assign wb_valid=!kill && complete;
 assign wb_side=secondary_multiply ? {held_side[64:32],mul_data} : held_side;
 wire[31:0] completed_result=memory_access ? loaded : primary_multiply ? mul_data : result;
 assign wb_packet={tag,pc,insn,next_pc,completed_result,address,store_data,
                  response_error ? address : tval,csr_data,
                  response_error ? (kind==5 ? 5'd7 : 5'd5) : cause,rd,f3,kind,wr,
                  exception || response_error,csr_we,serial};
SHAPE
 always @(posedge clk) begin
  if(start) begin held<=packet;held_side<=side_packet;end
  if(start && input_memory) begin
   load_word<=packet[10:8]==2;
   load_signed_byte<=packet[10:8]==0;load_signed_half<=packet[10:8]==1;
   load_byte_lane<=packet[9:8]==0 ? (4'b1<<input_address[1:0]) : 4'b0;
   load_half_lane<=packet[9:8]==1 ? (2'b1<<input_address[1]) : 2'b0;
  end
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin slot_valid<=0;sent<=0;end
  else if(kill) begin slot_valid<=0;sent<=0;end
  else begin
   if(start) begin slot_valid<=1;sent<=early_request && req_ready;end
   else begin
    if(complete) slot_valid<=0;
    if(old_request && req_ready) sent<=1;
   end
  end
 end
endmodule
'''.replace('SHAPE',shape)
 (out/'nc_memory.v').write_text(text)
 for name in ('nc_core.v','nc_memory.v'):g['override_sha256']['hardware\\pds\\source\\core\\'+name]=sha(out/name)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),parent_generation_sha256=sha(src/'generation.json'),accepted_dual_sha256=sha(accepted),scope=a.variant+'; uniform MEM ownership plus empty FIFO handoff, early primary local requests only in early variant; unchanged five-source operands/no raw load return/no secondary LSU; not adopted')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',a.variant)
if __name__=='__main__':main()
