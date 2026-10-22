"""Generate a research-only two-pop EX/MEM / second-entry load launch."""
def transform(core,fifo):
    old='output wire out_valid,input wire out_ready,output wire [WIDTH-1:0] out_data'
    assert old in fifo
    fifo=fifo.replace(old,old+',\n output wire next_valid,output wire[WIDTH-1:0] next_data,input wire pop_second')
    fifo=fifo.replace('assign out_data=data[rd];','assign out_data=data[rd];\n wire[PTR-1:0] following=rd+1\'b1;\n assign next_valid=count>1;assign next_data=data[following];')
    fifo=fifo.replace("if(pop) rd<=rd+1'b1;","if(pop) rd<=pop_second ? rd+2'd2 : rd+1'b1;")
    fifo=fifo.replace('case({push,pop})',"if(pop && pop_second) count<=push ? count-1'b1 : count-2'd2;\n   else case({push,pop})")
    core=core.replace('wire[183:0] compact_packet;', 'wire[183:0] compact_packet,next_compact;wire next_valid,pop_second;')
    core=core.replace('.out_data(compact_packet));','.out_data(compact_packet),.next_valid(next_valid),.next_data(next_compact),.pop_second(pop_second));')
    block='''
 // Experimental local two-entry consumption. All addresses are already in
 // EX/MEM registers. Input credit stays registered; no raw EX RAM request.
 wire base_ready,base_done,base_mul_consume;wire[279:0] base_packet;
 wire[2:0] unused_mul_tag;
 wire[279:0] following_load={next_compact[183:85],next_compact[84:53],next_compact[52:21],96'b0,next_compact[20:0]};
 wire head_mul=mem_valid && mem_packet[7:4]==6 && !mem_packet[10] && !mem_packet[2];
 wire next_ram=next_compact[52:21]<32'h00010000 ||
              (next_compact[52:21]>=32'h10000000 && next_compact[52:21]<32'h10008000);
 wire launch_second=next_valid && mem_valid && memory.state==0 && !do_trap && !mem_packet[2] &&
                    mem_packet[7:4]!=4 && mem_packet[7:4]!=5 && (!head_mul || mul_query_ready) &&
                    next_compact[7:4]==4 && !next_compact[2] && next_ram;
 wire[279:0] selected_mem_packet=launch_second ? following_load : mem_packet;
 assign mul_query_tag=mem_packet[279:277];
 assign mul_consume=base_mul_consume || (launch_second && base_ready && head_mul);
 assign memory_ready=base_ready;assign pop_second=launch_second && base_ready;
 assign memory_done=launch_second ? base_ready : base_done;
 assign memory_packet=launch_second ? (head_mul ? {mem_packet[279:181],mul_query_data,mem_packet[148:0]} : mem_packet) : base_packet;
'''
    needle=' nc_memory memory('
    assert needle in core;core=core.replace(needle,block+needle)
    core=core.replace('.ready(memory_ready),.packet(mem_packet)', '.ready(base_ready),.packet(selected_mem_packet)')
    core=core.replace('.mul_tag(mul_query_tag)', '.mul_tag(unused_mul_tag)').replace('.mul_consume(mul_consume)', '.mul_consume(base_mul_consume)')
    core=core.replace('.wb_valid(memory_done),.wb_packet(memory_packet)', '.wb_valid(base_done),.wb_packet(base_packet)')
    assert '.next_valid(next_valid)' in core and '.ready(base_ready)' in core
    return core,fifo
