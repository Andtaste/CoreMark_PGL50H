"""Isolated expansion from the accepted dual baseline, using verified window components."""
from pathlib import Path
import argparse,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_lsu_shared','dual_lsu_ports'),required=True);a=ap.parse_args()
 accepted=ROOT/'docs/accepted_dual_baseline.json';b=json.loads(accepted.read_text(encoding='utf-8'));assert b['variant']=='dual_fwd_share'
 for key in ('source_sha256','evidence_sha256','ip_sha256'):
  for n,h in b[key].items():assert sha(ROOT/n)==h,(key,n)
 src=ROOT/'simulation/results/load_bp_dual_legacy_fifo';out=src.with_name('load_bp_'+a.variant);assert not out.exists();out.mkdir();g=json.loads((src/'generation.json').read_text())
 for n,h in g['override_sha256'].items():
  p=src/Path(n).name;assert sha(p)==h;shutil.copyfile(p,out/p.name)
 shutil.copytree(src/'ipcore',out/'ipcore');shutil.copyfile(src/'pango_ram_wide_models.v',out/'pango_ram_wide_models.v')
 for name in ('nc_memory.v','nc_local_bus.v'):shutil.copyfile(ROOT/'simulation/research/dual_lsu'/name,out/name)
 p=out/'nc_fetch.v';s=p.read_text();s=rep(s,'|| (1 && multiply_op)),multiply_op,memory_op','|| (1 && multiply_op) || memory_op),multiply_op,memory_op');s=rep(s,'op!=7\'h23 && op!=7\'h63,reg_op || op==7\'h63,imm_op || reg_op || op==7\'h63',"op!=7'h23 && op!=7'h63,reg_op || op==7'h63 || op==7'h23,imm_op || reg_op || op==7'h63 || memory_op");p.write_text(s)
 p=out/'nc_core.v';s=p.read_text();s=rep(s,' input wire d_rsp_valid,output wire d_rsp_ready,input wire[31:0] d_rdata,input wire d_error,',' input wire d_rsp_valid,output wire d_rsp_ready,input wire[31:0] d_rdata,input wire d_error,\n output wire s_req_valid,input wire s_req_ready,output wire[31:0] s_addr,s_wdata,\n output wire[3:0] s_mask,output wire s_write,\n input wire s_rsp_valid,output wire s_rsp_ready,input wire[31:0] s_rdata,')
 s=rep(s,' wire w1_wr=!w1_branch;'," wire w1_store=w1_insn[6:0]==7'h23,w1_load=w1_insn[6:0]==7'h03;\n wire w1_wr=!w1_branch && !w1_store;")
 s=rep(s,"wire[4:0] w1_rd=w1_branch ? 5'b0 : w1_insn[11:7];","wire[4:0] w1_rd=w1_wr ? w1_insn[11:7] : 5'b0;")
 s=rep(s,' wire extended_pair=id_pair_flags[9] && id_pair_flags[3] && !id_prediction[31];'," wire side_mem_candidate=id1_kind==4 || id1_kind==5;\n wire extended_pair=id_pair_flags[9] && !side_mem_candidate && id_pair_flags[3] && !id_prediction[31];\n wire memory_pair=side_mem_candidate && id_kind!=1 && !id_prediction[31] && !id_prediction1[31];")
 s=rep(s,'(extended_pair && (id_insn1[6] || !id_prediction1[31])))','(extended_pair && (id_insn1[6] || !id_prediction1[31])) || memory_pair)')
 s=rep(s,"wire[3:0] id_side_kind=extended_pair ? (id_insn1[6] ? 4'd1 : 4'd6) : 4'd0;","wire[3:0] id_side_kind=side_mem_candidate ? id1_kind : extended_pair ? (id_insn1[6] ? 4'd1 : 4'd6) : 4'd0;")
 s=rep(s,' wire side_multiply=ex_side[223] && ex_side[203:200]==6;',' wire side_multiply=ex_side[223] && ex_side[203:200]==6;\n wire side_memory=ex_side[223] && (ex_side[203:200]==4 || ex_side[203:200]==5);\n wire side_store=ex_side[203:200]==5;\n wire[31:0] side_address=secondary_result[148:117];\n wire side_local=side_address<32\'h00010000 || (side_address>=32\'h10000000 && side_address<32\'h10008000);\n wire side_bad=side_memory && (secondary_result[2] || !side_local);\n wire side_replay=ex_fire && side_bad && !execute_packet[2] && !prediction_wrong;')
 s=rep(s,'wire side_execute=ex_side[223] && !execute_packet[2] && !prediction_wrong;','wire side_execute=ex_side[223] && !execute_packet[2] && !prediction_wrong && !side_bad;')
 s=rep(s,"wire[31:0] side_value=side_branch ? secondary_result[212:181] : side_multiply ? 32'b0 : secondary_result[180:149];","wire[31:0] side_value=side_store ? secondary_result[116:85] : side_branch ? secondary_result[212:181] : side_multiply ? 32'b0 : secondary_result[180:149];")
 s=rep(s,'wire[64:0] side_result={side_execute,secondary_result[244:213],side_value};','wire[96:0] side_result={side_execute,secondary_result[244:213],side_value,side_address};')
 s=rep(s,'side_execute && !side_branch && !side_multiply &&','side_execute && !side_branch && !side_multiply && !side_memory &&')
 s=rep(s,'wire[183:0] compact_packet;wire[64:0] compact_side,memory_side;','wire[183:0] compact_packet;wire[96:0] compact_side;wire[64:0] memory_side;')
 s=rep(s,'nc_fifo #(.WIDTH(249),.DEPTH(4))','nc_fifo #(.WIDTH(281),.DEPTH(4))')
 s=rep(s,'  .wb_valid(memory_done),.wb_packet(memory_packet),','  .req1_valid(s_req_valid),.req1_ready(s_req_ready),.req1_addr(s_addr),.req1_data(s_wdata),.req1_mask(s_mask),.req1_write(s_write),\n  .rsp1_valid(s_rsp_valid),.rsp1_ready(s_rsp_ready),.rsp1_data(s_rdata),\n  .wb_valid(memory_done),.wb_packet(memory_packet),')
 s=rep(s,'  .stats_events({','  .stats_events({commit1 && w1_store,commit1 && w1_load,')
 s=rep(s,'redirect_pc<=side_branch ? secondary_result[212:181] : execute_packet[212:181];','redirect_pc<=side_replay ? secondary_result[276:245] : side_branch ? secondary_result[212:181] : execute_packet[212:181];')
 s=rep(s,'if(branch_event) begin redirect<=1;branch_redirect<=1;end','if(branch_event || side_replay) begin redirect<=1;branch_redirect<=1;end')
 s=s.replace('// Isolated limited dual issue: ordered primary + dependency-free ALU sidecar.','// Ordered dual issue: ALU/branch/MUL and two restricted local-memory lanes.')
 p.write_text(s)
 p=out/'nc_csr.v';s=p.read_text().replace('input wire[13:0] stats_events','input wire[15:0] stats_events');p.write_text(s)
 p=out/'nc_stats.v';s=p.read_text().replace('input wire[13:0] events','input wire[15:0] events').replace('reg enabled;reg[13:0] sample,overflow;','reg enabled;reg[15:0] sample;reg[13:0] overflow;').replace("? events : 14'b0","? events : 16'b0")
 s=rep(s,'if(i!=8 && sample[i-1]) begin','if(i!=8 && (sample[i-1] || (i==11 && sample[14]) || (i==12 && sample[15]))) begin')
 s=rep(s,"counters[i]<=counters[i]+((i==9 && sample[9]) ? 32'd2 : 32'd1);","counters[i]<=counters[i]+(i==11 ? ({31'b0,sample[10]}+{31'b0,sample[14]}) : i==12 ? ({31'b0,sample[11]}+{31'b0,sample[15]}) : ((i==9 && sample[9]) ? 32'd2 : 32'd1));")
 s=rep(s,"if((&counters[i]) || (i==9 && sample[9] && counters[i]==32'hfffffffe))", "if((&counters[i]) || (counters[i]==32'hfffffffe && ((i==9 && sample[9]) || (i==11 && sample[10] && sample[14]) || (i==12 && sample[11] && sample[15]))))")
 p.write_text(s)
 p=out/'nc_soc.v';s=p.read_text();s=rep(s,' wire[63:0] idata;', ' wire sv,sr,sov,sor,swrite;wire[31:0] sa,sw,sdata;wire[3:0] sm;\n wire[63:0] idata;')
 s=rep(s,'  .trace_valid(),', '  .s_req_valid(sv),.s_req_ready(sr),.s_addr(sa),.s_wdata(sw),.s_mask(sm),.s_write(swrite),\n  .s_rsp_valid(sov),.s_rsp_ready(sor),.s_rdata(sdata),\n  .trace_valid(),')
 s=rep(s,' nc_local_bus bus(', ' nc_local_bus #(.SECOND_PORT('+str(int(a.variant=='dual_lsu_ports'))+')) bus(')
 s=rep(s,'  .uart_tx(uart_tx)', '  .sv(sv),.sr(sr),.sa(sa),.sw(sw),.sm(sm),.swrite(swrite),.sov(sov),.sor(sor),.sdata(sdata),\n  .uart_tx(uart_tx)');p.write_text(s)
 for p in out.glob('*.v'):
  for k in list(g['override_sha256']):
   if Path(k).name==p.name:g['override_sha256'][k]=sha(p)
 ips=[p for p in (out/'ipcore').rglob('*') if p.is_file() and p.suffix in ('.v','.idf')];g['ip_sha256']={str(p.relative_to(ROOT)):sha(p) for p in ips+[ROOT/'simulation/results/load_bp_dual_ram_logic/boot_interleaved.hex']}
 g.update(generator_sha256=sha(Path(__file__)),accepted_dual_sha256=sha(accepted),parent_generation_sha256=sha(src/'generation.json'),canonical_sha256={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'simulation/research/dual_lsu').glob('*.v')},scope=a.variant+'; accepted dual_fwd_share remains baseline; reuses verified individual-word FIFO/branch/MUL/4-source staging components only; adds secondary local RAM LSU with EX fallback for fault/MMIO and ordered stores; no early request or RAM-to-EX bypass; not adopted')
 (out/'generation.json').write_text(json.dumps(g,indent=2)+'\n');print('GENERATED',a.variant)
if __name__=='__main__':main()
