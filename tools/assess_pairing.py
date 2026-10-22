"""Collect same-window retirements, then assess greedy in-order dual pairing.

This is a structural opportunity model, not a dual-issue CPU simulator.
All counters/trace generation are inserted into a copied simulation TB only.
"""
from pathlib import Path
from functools import lru_cache
from collections import Counter
import argparse,gzip,hashlib,json,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
POLICIES=('full0_alu1','alu0_alu1','full0_alu1_branch_solo','full0_alu1_no_waw','full0_alu1_2r1w')

@lru_cache(maxsize=None)
def decode(insn):
    op=insn&127;rd=(insn>>7)&31;f3=(insn>>12)&7;ra=(insn>>15)&31;rb=(insn>>20)&31;f7=insn>>25
    if op in (0x37,0x17):kind='ALU';sources=();writes=rd
    elif op==0x13:kind='ALU';sources=(ra,);writes=rd
    elif op==0x33:kind=('MUL' if f3<4 else 'DIV') if f7==1 else 'ALU';sources=(ra,rb);writes=rd
    elif op==3:kind='LOAD';sources=(ra,);writes=rd
    elif op==0x23:kind='STORE';sources=(ra,rb);writes=0
    elif op==0x63:kind='BRANCH';sources=(ra,rb);writes=0
    elif op==0x6f:kind='JAL';sources=();writes=rd
    elif op==0x67:kind='JALR';sources=(ra,);writes=rd
    elif op==0x73:kind='SERIAL';sources=(ra,) if f3 and not (f3&4) else ();writes=rd if f3 else 0
    elif op==0xf:kind='SERIAL';sources=();writes=0
    else:raise AssertionError(f'Unsupported retired instruction {insn:08x}')
    return kind,frozenset(x for x in sources if x),writes

def reason(a,b,policy):
    # Rows: PC, instruction, actual next-PC, saved EX prediction mismatch, cycle.
    ka,sa,wa=decode(a[1]);kb,sb,wb=decode(b[1])
    if kb!='ALU':return 'second_'+kb.lower()
    if ka=='SERIAL':return 'first_serial'
    if b[0]!=(a[0]+4)&0xffffffff or a[2]!=(a[0]+4)&0xffffffff:return 'nonsequential_flow'
    if a[3]:return 'first_prediction_recovery'
    if policy=='alu0_alu1' and ka!='ALU':return 'first_not_alu'
    if policy=='full0_alu1_branch_solo' and ka in ('BRANCH','JAL','JALR'):return 'first_control_solo'
    if wa and wa in sb:return 'raw_'+ka.lower()
    if policy=='full0_alu1_no_waw' and wa and wa==wb:return 'waw'
    if policy=='full0_alu1_2r1w':
        if len(sa|sb)>2:return 'read_ports'
        if len({x for x in (wa,wb) if x})>1:return 'write_ports'
    return None

def assess(trace,expected_retired,expected_cycles):
    pending={k:None for k in POLICIES};pairs=Counter();reject={k:Counter() for k in POLICIES}
    types={k:Counter() for k in POLICIES};reads={k:Counter() for k in POLICIES};writes={k:Counter() for k in POLICIES}
    gaps={k:Counter() for k in POLICIES};waw=Counter();war=Counter();opcodes=Counter();adj=Counter();adj_reject=Counter()
    counts=0;previous=None;bad_predictions=0;last_cycle=0
    opener=gzip.open if trace.suffix=='.gz' else open
    with opener(trace,'rt',encoding='ascii') as f:
        for line in f:
            row=tuple(int(x,16) for x in line.split());assert len(row)==5,row
            pc,insn,nxt,bad,cycle=row;assert bad in (0,1) and cycle>last_cycle
            assert cycle<=expected_cycles
            last_cycle=cycle;counts+=1;bad_predictions+=bad;opcodes[decode(insn)[0]]+=1
            if previous is not None:
                assert pc==previous[2],f'Retirement flow discontinuity {previous!r} {row!r}'
                why=reason(previous,row,'full0_alu1')
                if why is None:adj['eligible']+=1
                else:adj_reject[why]+=1
            previous=row
            for policy in POLICIES:
                old=pending[policy]
                if old is None:pending[policy]=row;continue
                why=reason(old,row,policy)
                if why is not None:
                    reject[policy][why]+=1;pending[policy]=row;continue
                pairs[policy]+=1;pending[policy]=None
                kind,src0,dst0=decode(old[1]);_,src1,dst1=decode(row[1])
                types[policy][kind+'+ALU']+=1;reads[policy][str(len(src0|src1))]+=1
                writes[policy][str(len({x for x in (dst0,dst1) if x}))]+=1
                if dst0 and dst0==dst1:waw[policy]+=1
                if dst1 and dst1 in src0:war[policy]+=1
                gap=row[4]-old[4];gaps[policy][str(gap) if gap<5 else '5+']+=1
    assert counts==expected_retired,(counts,expected_retired)
    policies={}
    for policy in POLICIES:
        p=pairs[policy];assert sum(types[policy].values())==p
        assert sum(reject[policy].values())==counts-2*p-(pending[policy] is not None)
        policies[policy]=dict(pairs=p,single_instructions=counts-2*p,ideal_issue_groups=counts-p,
            paired_instruction_fraction=2*p/counts,dual_group_fraction=p/(counts-p),
            width_only_ideal_ipc=counts/(counts-p),issue_group_reduction_fraction=p/counts,
            pair_types=dict(types[policy]),unique_read_registers=dict(reads[policy]),
            unique_write_registers=dict(writes[policy]),same_destination_pairs=waw[policy],war_pairs=war[policy],
            baseline_retirement_gap_histogram=dict(gaps[policy]),rejection_priority_counts=dict(reject[policy]))
    return dict(retired=counts,baseline_cycles=expected_cycles,retired_bad_predictions=bad_predictions,
        instruction_classes=dict(opcodes),adjacent_eligible=adj['eligible'],
        adjacent_eligible_fraction=adj['eligible']/max(1,counts-1),adjacent_rejection_priority_counts=dict(adj_reject),policies=policies)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--reference',required=True)
    parser.add_argument('--result-tag',default='final')
    parser.add_argument('--analyze-only',action='store_true')
    args=parser.parse_args();assert re.fullmatch(r'[A-Za-z0-9_-]+',args.result_tag)
    out=ROOT/('simulation/results/pair_'+args.result_tag);out.mkdir(parents=True,exist_ok=True)
    ref=json.loads((ROOT/args.reference).read_text());assert ref['status']=='PASS'
    trace=out/'retirements.txt';archive=out/'retirements.txt.gz'
    if not args.analyze_only:
        rtl=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[])
        model=ROOT/'simulation/models/pango_ram_models.v';tb_source=ROOT/'simulation/tb/soc_tb.v'
        image=ROOT/'sw/build/coremark_performance_10/coremark.hex';uart_source=ROOT/'hardware/pds/source/perips/nc_uart.v'
        inputs=rtl+[model,tb_source,image,Path(__file__).resolve()]
        hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
        tb=tb_source.read_text().replace(' defparam dut.bus.uart.BAUD=9375000;','')
        tb=tb.replace(' reg check_stats=0;',''' reg check_stats=0;
 integer pair_fd=0,pair_count=0;reg[1023:0] pair_file;reg[7:0] pair_bad=0;
 initial if(!$value$plusargs("pairtrace=%s",pair_file)) $fatal(1,"missing pair trace");
 always @(posedge clk) if(rst_n && dut.cpu.ex_fire) pair_bad[dut.cpu.ex_tag]<=dut.cpu.prediction_wrong;
''',1)
        tb=tb.replace('    ref_cycles=0;ref_retired=0;ref_loads=0;ref_stores=0;ref_bjp=0;','''    ref_cycles=0;ref_retired=0;ref_loads=0;ref_stores=0;ref_bjp=0;
    if(pair_fd) $fclose(pair_fd);pair_fd=$fopen(pair_file,"w");pair_count=0;
''',1)
        tb=tb.replace('   if(dut.cpu.commit) begin','''   if(dut.cpu.commit) begin
    pair_count=pair_count+1;
    $fdisplay(pair_fd,"%08x %08x %08x %01x %08x",dut.cpu.w_pc,dut.cpu.w_insn,dut.cpu.w_next,pair_bad[dut.cpu.w_tag],ref_cycles);
''',1)
        tb=tb.replace(' always @(negedge clk) if(check_stats) begin',''' always @(negedge clk) if(check_stats) begin
  if(pair_count!=ref_retired) $fatal(1,"pair trace window mismatch");
  $fclose(pair_fd);pair_fd=0;$display("PAIR_TRACE_PASS count=%0d",pair_count);
''',1)
        tb_path=out/'soc_tb_pair.v';tb_path.write_text(tb)
        uart=out/'nc_uart_sim.v';uart.write_text(uart_source.read_text().replace('BAUD=115200','BAUD=9375000'))
        def linux(p):
            p=Path(p).resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
        prefix=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--']
        sources=[p for p in rtl if p!=uart_source]+[uart,model,tb_path]
        with (out/'compile.log').open('w') as f:
            subprocess.run([*prefix,'verilator','--binary','--timing','-j','4','-Wno-fatal','-DCOREMARK_SIM','--top-module','soc_tb','--Mdir',linux(out/'obj'),*[linux(p) for p in sources]],stdout=f,stderr=subprocess.STDOUT,check=True)
        with (out/'simulation.log').open('w') as f:
            subprocess.run([*prefix,linux(out/'obj/Vsoc_tb'),f'+image={linux(image)}',f'+trace={linux(out)}/unused.trace',f'+uart={linux(out)}/uart.txt',f'+pairtrace={linux(trace)}','+notrace=1','+limit=33000000'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
        log=(out/'simulation.log').read_text(encoding='utf-8',errors='replace');text=(out/'uart.txt').read_text(encoding='utf-8')
        assert f"PAIR_TRACE_PASS count={ref['metrics']['Retired instructions']}" in log
        assert 'COUNTER_CHECK_PASS' in log and 'CRC validation   : PASS' in text
        for key,value in ref['metrics'].items():
            assert any(line.split(':',1)[0].strip()==key and line.split(':',1)[1].strip()==value for line in text.splitlines() if ':' in line),key
        for name,digest in hashes.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
        collection=dict(status='PASS',input_sha256=hashes,tb_sha256=hashlib.sha256(tb_path.read_bytes()).hexdigest(),reference=args.reference,
            image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest())
        (out/'collection.json').write_text(json.dumps(collection,indent=2)+'\n')
        with trace.open('rb') as src,gzip.open(archive,'wb',compresslevel=6) as dst:shutil.copyfileobj(src,dst)
        trace.unlink() # Only this tool's just-created trace; compressed evidence remains.
    result=assess(archive,int(ref['metrics']['Retired instructions']),int(ref['metrics']['Stats window cycles']))
    result.update(status='PASS',scope='Structural greedy pairing of retired path, not implemented dual IPC',
        rules=['Slot 0 ordinary RV32IM; slot 1 LUI/AUIPC/OP-IMM/non-M OP only.',
            'No instruction skip/reorder; no same-pair RAW bypass; x0 is not a dependency.',
            'Only consecutive PC and sequential actual next-PC; no pairing with a taken target.',
            'A slot-0 prediction recovery serializes that candidate; CSR/system/fence serialize.',
            'Primary policy assumes up to four unique RF reads and two unique RF writes; WAW uses younger priority.',
            'Operand readiness, memory/MUL occupancy, RF timing, fetch bandwidth and dual retirement are NOT simulated.',
            'Rejection counts are priority partitions, not independent loss estimates.'],
        trace_gzip_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(retired=result['retired'],policies={k:{a:v[a] for a in ('pairs','paired_instruction_fraction','width_only_ideal_ipc')} for k,v in result['policies'].items()}),indent=2))
if __name__=='__main__':main()
