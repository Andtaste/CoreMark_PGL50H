"""Generate an isolated, limited two-issue candidate from the accepted source.
Production RTL/IP/images are read-only. Canonical handwritten modules live in
simulation/research/dual_issue; generated modules and results are isolated.
"""
from pathlib import Path
import hashlib,json,argparse
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'simulation/results/load_bp_dual_issue'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
def main():
    global OUT
    ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('dual_issue','dual_issue_finish'),default='dual_issue');args=ap.parse_args()
    OUT=ROOT/('simulation/results/load_bp_'+args.variant)
    OUT.mkdir(exist_ok=True)
    accepted=json.loads((ROOT/'docs/accepted_baseline.json').read_text(encoding='utf-8'))
    for p,h in accepted['source_sha256'].items():assert sha(ROOT/p)==h,p
    def read(n):return (ROOT/'hardware/pds/source/core'/n).read_text()
    def save(n,s):(OUT/n).write_text(s,encoding='utf-8')
    for n in ('nc_fetch.v','nc_regfile.v'):save(n,(ROOT/'simulation/research/dual_issue'/n).read_text())
    s=read('nc_operands.v')
    s=rep(s,'input wire[18:0] in_control,','input wire[223:0] in_side,output wire[223:0] out_side,\n input wire[18:0] in_control,')
    s=rep(s,'reg[203:0] payload[0:1];reg[2:0] token[0:1],dep_a[0:1],dep_b[0:1];',
          'reg[223:0] side[0:1];assign out_side=side[rd];\n reg[203:0] payload[0:1];reg[2:0] token[0:1];reg[3:0] dep_a[0:1],dep_b[0:1];')
    for n in ('tag_a,tag_b','f_tag','w_tag','m_tag'):s=s.replace('input wire[2:0] '+n,'input wire[3:0] '+n)
    s=rep(s,'output wire occupied);','input wire f1_valid,w1_valid,input wire[3:0] f1_tag,w1_tag,input wire[31:0] f1_data,w1_data,\n output wire occupied);')
    s=rep(s,'wire[1:0] hit_ma,hit_mb;','wire[1:0] hit_ma,hit_mb,hit_f1a,hit_f1b,hit_w1a,hit_w1b;')
    for x,wait in (('a','wa'),('b','wb')):
        s=rep(s,f'assign selected_v{x}[s]={wait}[s] ? (hit_f{x}[s] ? f_data : hit_m{x}[s] ? m_data : w_data) : v{x}[s];',
              f'assign hit_f1{x}[s]=f1_valid && f1_tag==dep_{x}[s];assign hit_w1{x}[s]=w1_valid && w1_tag==dep_{x}[s];\n'+
              f'  assign selected_v{x}[s]={wait}[s] ? (hit_f{x}[s] ? f_data : hit_f1{x}[s] ? f1_data : hit_m{x}[s] ? m_data : hit_w{x}[s] ? w_data : w1_data) : v{x}[s];')
        s=rep(s,f'!{wait}[s] || hit_f{x}[s] || hit_m{x}[s] || hit_w{x}[s];',
              f'!{wait}[s] || hit_f{x}[s] || hit_f1{x}[s] || hit_m{x}[s] || hit_w{x}[s] || hit_w1{x}[s];')
        s=rep(s,f'else if({wait}[i] && hit_m{x}[i])',f'else if({wait}[i] && hit_f1{x}[i]) begin v{x}[i]<=f1_data;{wait}[i]<=0;end\n   else if({wait}[i] && hit_m{x}[i])')
        s=rep(s,f'else if({wait}[i] && hit_w{x}[i]) begin v{x}[i]<=w_data;{wait}[i]<=0;end',
              f'else if({wait}[i] && hit_w{x}[i]) begin v{x}[i]<=w_data;{wait}[i]<=0;end\n   else if({wait}[i] && hit_w1{x}[i]) begin v{x}[i]<=w1_data;{wait}[i]<=0;end')
        s=rep(s,f'else if(wait_{x} && m_valid',f'else if(wait_{x} && f1_valid && tag_{x}==f1_tag) begin v{x}[wr]<=f1_data;{wait}[wr]<=0;end\n   else if(wait_{x} && m_valid')
        s=rep(s,f'else if(wait_{x} && w_valid && tag_{x}==w_tag) begin v{x}[wr]<=w_data;{wait}[wr]<=0;end',
              f'else if(wait_{x} && w_valid && tag_{x}==w_tag) begin v{x}[wr]<=w_data;{wait}[wr]<=0;end\n   else if(wait_{x} && w1_valid && tag_{x}==w1_tag) begin v{x}[wr]<=w1_data;{wait}[wr]<=0;end')
    s=rep(s,'payload[wr]<=in_packet;','side[wr]<=in_side;payload[wr]<=in_packet;')
    save('nc_operands.v',s)
    s=read('nc_memory.v')
    s=rep(s,'input wire[279:0] packet,','input wire[101:0] side_packet,output wire[101:0] wb_side,\n input wire[279:0] packet,')
    s=rep(s,'reg[279:0] held;','reg[279:0] held;reg[101:0] held_side;\n assign wb_side=(memory_pending || buffered) ? held_side : side_packet;')
    s=rep(s,'if(valid && ready && (input_memory || state!=IDLE)) held<=completed_input;',
          'if(valid && ready && (input_memory || state!=IDLE)) begin held<=completed_input;held_side<=side_packet;end')
    save('nc_memory.v',s)
    s=read('nc_csr.v')
    s=rep(s,'input wire clk,rst_n,retire,','input wire clk,rst_n,retire,retire1,')
    s=rep(s,"if(retire) instret<=instret+1'b1;","if(retire) instret<=instret+(retire1 ? 64'd2 : 64'd1);")
    save('nc_csr.v',s)
    s=read('nc_stats.v')
    s=rep(s,'   10:data=0; // Single issue; no secondary retirement slot.\n','')
    s=rep(s,'if(i!=8 && i!=10 && sample[i-1]) begin','if(i!=8 && sample[i-1]) begin')
    s=rep(s,"counters[i]<=counters[i]+1'b1;","counters[i]<=counters[i]+((i==9 && sample[9]) ? 32'd2 : 32'd1);")
    s=s.replace('if(&counters[i]) overflow[i-1]<=1;',"if((&counters[i]) || (i==9 && sample[9] && counters[i]==32'hfffffffe)) overflow[i-1]<=1;")
    save('nc_stats.v',s)
    s=read('nc_core.v')
    s=s.replace('// Original five-stage single-issue RV32IM core, optional 64-entry BTB.',
      '// Isolated limited dual issue: ordered primary + dependency-free ALU sidecar.\n// One ledger token per atomic retirement group; dependency IDs include lane.')
    s=rep(s,'input wire i_rsp_valid,output wire i_rsp_ready,input wire[31:0] i_data,','input wire i_rsp_valid,output wire i_rsp_ready,input wire[63:0] i_data,')
    s=rep(s,'reg barrier;reg[7:0] live;','reg[4:0] destination1[0:7];\n reg barrier;reg[7:0] live;')
    s=rep(s,'wire id_valid,id_fault,id_ready;wire[31:0] id_pc,id_insn;',
      'wire id_valid,id_fault,id_ready,id_second,pair_issue;wire[31:0] id_pc,id_insn,id_insn1,id_prediction1;')
    s=rep(s,'wire commit=wb_valid && !w_fault;',
      'wire[101:0] w_side;wire commit=wb_valid && !w_fault;\n wire commit1=commit && w_side[101];\n wire[31:0] w1_pc=w_side[100:69],w1_insn=w_side[68:37],w1_result=w_side[36:5];\n wire[4:0] w1_rd=w_side[4:0];')
    s=rep(s,'.valid(id_valid),.ready(id_ready),.pc(id_pc),.inst(id_insn),.fault(id_fault));',
      '.valid(id_valid),.ready(id_ready),.take_two(pair_issue),.second_valid(id_second),\n  .prediction1(id_prediction1),.inst1(id_insn1),.pc(id_pc),.inst(id_insn),.fault(id_fault));')
    s=rep(s,'nc_regfile rf(.clk(clk),.we(commit && w_wr),.wa(w_rd),.wd(w_result),.ra(rs1),.rb(rs2),.a(a),.b(b));',
      '''wire[3:0] id1_kind;wire[31:0] id1_imm,c,d;wire id1_use1,id1_use2,id1_wr,id1_serial,id1_illegal;
 wire[4:0] rs1_1,rs2_1,rd1;wire[18:0] id1_control;
 nc_decode decode1(.insn(id_insn1),.kind(id1_kind),.imm(id1_imm),.use1(id1_use1),.use2(id1_use2),
  .write_rd(id1_wr),.serial(id1_serial),.illegal(id1_illegal),.rs1(rs1_1),.rs2(rs2_1),.rd(rd1),
  .csr_exists(1'b0),.csr_writable(1'b0),.control(id1_control));
 nc_regfile rf(.clk(clk),.we(commit && w_wr),.wa(w_rd),.wd(w_result),.ra(rs1),.rb(rs2),.a(a),.b(b),
  .we1(commit1),.wa1(w1_rd),.wd1(w1_result),.rc(rs1_1),.rd(rs2_1),.c(c),.d(d));''')
    s=rep(s,'reg dep_a,dep_b;reg[2:0] tag_a,tag_b;integer n;',
      'reg dep_a,dep_b,second_dep;reg[3:0] tag_a,tag_b;integer n;reg[7:0] match_a1,match_b1;')
    s=rep(s,'match_a=0;match_b=0;below_tail=0;','match_a=0;match_b=0;match_a1=0;match_b1=0;below_tail=0;second_dep=0;')
    s=rep(s,'''   if(live[n] && destination[n]!=0) begin
    match_a[n]=destination[n]==rs1;
    match_b[n]=destination[n]==rs2;
   end''','''   if(live[n]) begin
    match_a[n]=destination[n]!=0 && destination[n]==rs1;
    match_b[n]=destination[n]!=0 && destination[n]==rs2;
    match_a1[n]=destination1[n]!=0 && destination1[n]==rs1;
    match_b1[n]=destination1[n]!=0 && destination1[n]==rs2;
    if((id1_use1 && rs1_1!=0 && (destination[n]==rs1_1 || destination1[n]==rs1_1)) ||
       (id1_use2 && rs2_1!=0 && (destination[n]==rs2_1 || destination1[n]==rs2_1))) second_dep=1;
   end''')
    s=rep(s,'''  tag_a=|(match_a & below_tail) ? newest(match_a & below_tail) : newest(match_a);
  tag_b=|(match_b & below_tail) ? newest(match_b & below_tail) : newest(match_b);
  dep_a=use1 && |match_a;dep_b=use2 && |match_b;''','''  tag_a[3:1]=|((match_a|match_a1) & below_tail) ? newest((match_a|match_a1) & below_tail) : newest(match_a|match_a1);
  tag_b[3:1]=|((match_b|match_b1) & below_tail) ? newest((match_b|match_b1) & below_tail) : newest(match_b|match_b1);
  tag_a[0]=match_a1[tag_a[3:1]];tag_b[0]=match_b1[tag_b[3:1]];
  dep_a=use1 && |(match_a|match_a1);dep_b=use2 && |(match_b|match_b1);''')
    s=rep(s,'reg f_valid;reg[2:0] f_tag;reg[31:0] f_data;','reg f_valid;reg[2:0] f_tag;reg[31:0] f_data;\n reg f1_valid;reg[2:0] f1_tag;reg[31:0] f1_data;')
    s=rep(s,'assign id_ready=issue;', '''// Pair only a clean sequential non-control primary with a plain ALU.
 // Lane1 never waits: any live source producer or intra-pair RAW splits
 // the group. Lane0 therefore always progresses independently of lane1.
 wire pair_candidate=id_second && !id_fault && !id_illegal && !id_serial &&
  (id_kind==0 || id_kind==4 || id_kind==5 || (id_kind==6 && !id_insn[14])) &&
  !id_prediction[30] && !id_prediction1[31] && id1_kind==0 && !id1_illegal && !id1_serial &&
  !second_dep && !(id_wr && rd!=0 && ((id1_use1 && rd==rs1_1) || (id1_use2 && rd==rs2_1))) &&
  !(id_wr && rd!=0 && rd==rd1);
 assign pair_issue=issue && pair_candidate;
 assign id_ready=issue;
 wire[223:0] ex_side;
 wire[223:0] id_side={pair_candidate,id1_control,4'b0,id_pc+32'd4,id_insn1,c,d,id1_imm,32'b0,rd1,id1_wr,2'b0};''')
    s=rep(s,'.in_valid(issue),.in_ready(ex_credit),.in_tag(tail),','.in_valid(issue),.in_ready(ex_credit),.in_tag(tail),.in_side(id_side),.out_side(ex_side),')
    s=rep(s,'.f_valid(f_valid),.f_tag(f_tag),.f_data(f_data),',
      '.f_valid(f_valid),.f_tag({f_tag,1\'b0}),.f_data(f_data),\n  .f1_valid(f1_valid),.f1_tag({f1_tag,1\'b1}),.f1_data(f1_data),\n  .w1_valid(commit1 && w1_rd!=0),.w1_tag({w_tag,1\'b1}),.w1_data(w1_result),')
    s=rep(s,'.w_tag(w_tag),.w_data(w_result),',".w_tag({w_tag,1'b0}),.w_data(w_result),")
    s=rep(s,'.m_valid(m_valid),.m_tag(m_tag),.m_data(m_data),',".m_valid(m_valid),.m_tag({m_tag,1'b0}),.m_data(m_data),")
    s=rep(s,'wire ex_fire=execute_valid && mem_credit;', '''wire ex_fire=execute_valid && mem_credit;
 wire[276:0] secondary_result;
 nc_execute execute1(.clk(clk),.rst_n(rst_n),.clear(redirect || do_trap),
  .valid(ex_valid && ex_enable && ex_side[223]),.ready(),.packet(ex_side[203:0]),.control(ex_side[222:204]),
  .redirect_needed(),.redirect_target(),.prediction(32'b0),.prediction_wrong(),.branch_taken(),
  .out_valid(),.out_ready(mem_credit),.out_packet(secondary_result),.memory_aux());
 wire side_execute=ex_side[223] && !execute_packet[2] && !prediction_wrong;
 wire[101:0] side_result={side_execute,secondary_result[276:213],secondary_result[180:149],secondary_result[15:11]};
 always @(posedge clk) if(ex_fire) begin f1_tag<=ex_tag;f1_data<=secondary_result[180:149];end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) f1_valid<=0;else f1_valid<=ex_fire && side_execute && secondary_result[15:11]!=0;
 end''')
    s=rep(s,'wire[183:0] compact_packet;','wire[183:0] compact_packet;wire[101:0] compact_side,memory_side;')
    s=rep(s,'nc_fifo #(.WIDTH(184),.DEPTH(4)) memory_queue','nc_fifo #(.WIDTH(286),.DEPTH(4)) memory_queue')
    s=rep(s,'.in_data({ex_tag,execute_packet[276:181],queue_value,queue_aux,execute_packet[20:0]}),',
      '.in_data({side_result,ex_tag,execute_packet[276:181],queue_value,queue_aux,execute_packet[20:0]}),')
    s=rep(s,'.out_data(compact_packet));','.out_data({compact_side,compact_packet}));')
    s=rep(s,'nc_memory memory(.clk(clk),','nc_memory memory(.side_packet(compact_side),.wb_side(memory_side),.clk(clk),')
    s=rep(s,'reg wb_v;reg[279:0] wb_q;', 'reg[101:0] wb_side_q;assign w_side=wb_side_q;\n reg wb_v;reg[279:0] wb_q;')
    s=rep(s,'always @(posedge clk) if(memory_done) wb_q<=memory_packet;',
      'always @(posedge clk) if(memory_done) begin wb_q<=memory_packet;wb_side_q<=memory_side;end')
    s=rep(s,'.retire(commit),.raddr', '.retire(commit),.retire1(commit1),.raddr')
    s=rep(s,"1'b0,commit,1'b0,", "commit1,commit,1'b0,")
    s=rep(s,'for(r=0;r<8;r=r+1) destination[r]<=0;',
      'for(r=0;r<8;r=r+1) begin destination[r]<=0;destination1[r]<=0;end')
    s=rep(s,'if(issue) begin live[tail]<=1;destination[tail]<=id_wr ? rd : 0;tail<=tail+1\'b1;end',
      "if(issue) begin live[tail]<=1;destination[tail]<=id_wr ? rd : 0;destination1[tail]<=pair_candidate ? rd1 : 0;tail<=tail+1'b1;end")
    s=rep(s,'if(commit) arch_pc<=do_mret ? return_pc : w_next;',
      "if(commit) arch_pc<=do_mret ? return_pc : commit1 ? w1_pc+32'd4 : w_next;")
    s=rep(s,'integer r;','''// Secondary trace follows primary trace on the same cycle, never a
 // separate architectural transaction that could pass a primary fault.
 reg trace1_valid;reg[31:0] trace1_pc,trace1_insn,trace1_data;reg[4:0] trace1_rd;
 always @(posedge clk) begin
  trace1_pc<=w1_pc;trace1_insn<=w1_insn;trace1_rd<=w1_rd;trace1_data<=w1_rd!=0 ? w1_result : 0;
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) trace1_valid<=0;else trace1_valid<=commit1;
 end
 integer r;''')
    if args.variant=='dual_issue_finish':
        s=rep(s,''' wire pair_candidate=id_second && !id_fault && !id_illegal && !id_serial &&
  (id_kind==0 || id_kind==4 || id_kind==5 || (id_kind==6 && !id_insn[14])) &&
  !id_prediction[30] && !id_prediction1[31] && id1_kind==0 && !id1_illegal && !id1_serial &&
  !second_dep && !(id_wr && rd!=0 && ((id1_use1 && rd==rs1_1) || (id1_use2 && rd==rs2_1))) &&
  !(id_wr && rd!=0 && rd==rd1);''',''' // Pair legality has its own opcode-local decode. Full CSR legality is
 // intentionally absent from this control cone. Both decoders remain
 // authoritative for executing/trapping each instruction.
 wire[6:0] pair_op=id_insn[6:0],pair_f7=id_insn[31:25];wire[2:0] pair_f3=id_insn[14:12];
 wire primary_alu_legal=pair_op==7'h37 || pair_op==7'h17 ||
  (pair_op==7'h13 && !(pair_f3==1 && pair_f7!=0) && !(pair_f3==5 && pair_f7!=0 && pair_f7!=7'h20)) ||
  (pair_op==7'h33 && (pair_f7==0 || (pair_f7==7'h20 && (pair_f3==0 || pair_f3==5))));
 wire primary_pair_legal=primary_alu_legal ||
  (pair_op==7'h03 && (pair_f3==0 || pair_f3==1 || pair_f3==2 || pair_f3==4 || pair_f3==5)) ||
  (pair_op==7'h23 && pair_f3<=2) || (pair_op==7'h33 && pair_f7==1 && !pair_f3[2]);
 wire primary_pair_write=pair_op!=7'h23;
 wire pair_candidate=id_second && !id_fault && primary_pair_legal &&
  !id_prediction[30] && !id_prediction1[31] && id1_kind==0 && !id1_illegal && !id1_serial &&
  !second_dep && !(primary_pair_write && rd!=0 && ((id1_use1 && rd==rs1_1) || (id1_use2 && rd==rs2_1))) &&
  !(primary_pair_write && rd!=0 && rd==rd1);''')
    save('nc_core.v',s)
    # Widen IF, reusing generated Pango IP. Coherent replicated memories
    # provide both instruction words while preserving a dedicated LSU port.
    s=(ROOT/'hardware/pds/source/top/nc_soc.v').read_text()
    s=rep(s,'wire[31:0] ia,idata,da,dw,ddata;', 'wire[63:0] idata;wire[31:0] ia,da,dw,ddata;')
    save('nc_soc.v',s)
    s=(ROOT/'hardware/pds/source/sys_bus/nc_local_bus.v').read_text()
    s=rep(s,'output wire[31:0] idata,','output wire[63:0] idata,')
    s=rep(s,'wire[31:0] iq0,iq1,dq0,dq1;',
      "wire[31:0] iq0,iq1,iq0_hi,iq1_hi,dq0,dq1;\n wire[31:0] ia_lo={ia[31:3],3'b000},ia_hi={ia[31:3],3'b100};")
    s=rep(s,'ia[15:2]==da[15:2]', 'ia[15:3]==da[15:3]')
    s=rep(s,'assign idata=ibank ? iq1 : iq0;', 'assign idata=ibank ? {iq1_hi,iq1} : {iq0_hi,iq0};')
    s=s.replace('.a_addr(ia[15:2])','.a_addr(ia_lo[15:2])').replace('.a_addr(ia[14:2])','.a_addr(ia_lo[14:2])')
    for name,typ,bank,addr,iq in (('code','ram1_tdp','0','15:2','iq0'),('data','ram2_tdp','1','14:2','iq1')):
        start=s.index(' '+typ+' ram_'+name+'(');end=s.index('));',start)+3
        block=s[start:end]
        mirror=block.replace('ram_'+name+'(','ram_'+name+'_hi(').replace('ia_lo[','ia_hi[').replace('.a_rd_data('+iq+')','.a_rd_data('+iq+'_hi)').replace('.b_rd_data(dq'+bank+')','.b_rd_data()')
        s=s[:end]+'\n'+mirror+s[end:]
    save('nc_local_bus.v',s)
    overrides={}
    for p in sorted(OUT.glob('nc_*.v')):
        originals=list((ROOT/'hardware/pds/source').rglob(p.name));assert len(originals)==1,p
        overrides[str(originals[0].relative_to(ROOT))]=sha(p)
    result=dict(status='GENERATED',scope='Isolated limited dual-issue trial, not adopted',override_sha256=overrides,
      baseline_sha256=sha(ROOT/'docs/accepted_baseline.json'),generator_sha256=sha(Path(__file__)))
    (OUT/'generation.json').write_text(json.dumps(result,indent=2)+'\n')
    print('GENERATED',len(overrides),'overrides')
if __name__=='__main__':main()
