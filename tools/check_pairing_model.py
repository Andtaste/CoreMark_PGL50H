"""Semantic checks for the offline pairing assessment (no CPU RTL changes)."""
from pathlib import Path
import hashlib,json
from assess_pairing import ROOT,decode,reason,assess

def main():
    def addi(rd,rs,imm=0):return ((imm&4095)<<20)|(rs<<15)|(rd<<7)|0x13
    def add(rd,a,b):return (b<<20)|(a<<15)|(rd<<7)|0x33
    def row(pc,insn,nxt=None,bad=0,cycle=1):return pc,insn,pc+4 if nxt is None else nxt,bad,cycle
    assert decode(addi(5,0,7))==('ALU',frozenset(),5)
    assert decode(addi(7,1,5))==('ALU',frozenset((1,)),7) # imm[4:0] is not rs2.
    assert decode((5<<15)|(6<<20)|0x23)==('STORE',frozenset((5,6)),0)
    assert decode(0x000002b7)==('ALU',frozenset(),5)
    assert decode(0x0052d3f3)==('SERIAL',frozenset(),7) # CSRRWI: zimm is not a register read.
    a=row(0,addi(5,0));b=row(4,addi(6,5))
    assert reason(a,b,'full0_alu1')=='raw_alu'
    assert reason(row(0,addi(0,1)),row(4,addi(6,0)),'full0_alu1') is None
    assert reason(a,row(4,addi(6,1,5)),'full0_alu1') is None
    assert reason(a,row(4,addi(5,0)),'full0_alu1') is None
    assert reason(a,row(4,addi(5,0)),'full0_alu1_no_waw')=='waw'
    assert reason(row(0,add(5,6,1)),row(4,addi(6,0)),'full0_alu1') is None # WAR is legal.
    assert reason(row(0,add(5,1,2)),row(4,add(6,3,4)),'full0_alu1_2r1w')=='read_ports'
    assert reason(a,row(4,addi(6,0)),'full0_alu1_2r1w')=='write_ports'
    branch=0x00000463 # BEQ x0,x0,+8; use separately supplied actual next PC.
    assert reason(row(0,branch,4),row(4,addi(6,0)),'full0_alu1') is None
    assert reason(row(0,branch,4),row(4,addi(6,0)),'full0_alu1_branch_solo')=='first_control_solo'
    assert reason(row(0,branch,8),row(8,addi(6,0)),'full0_alu1')=='nonsequential_flow'
    assert reason(row(0,branch,4,1),row(4,addi(6,0)),'full0_alu1')=='first_prediction_recovery'
    # Nine architectural instructions have four eligible adjacent edges,
    # but only three non-overlapping greedy pairs. RAW/fence stay in order.
    load=(1<<15)|(2<<12)|(5<<7)|3
    store=(7<<20)|(1<<15)|(2<<12)|0x23
    program=(load,addi(6,5),addi(7,0),store,addi(8,0),0x0000000f,addi(9,0),addi(10,0),addi(11,0))
    out=ROOT/'simulation/results/pair_model';out.mkdir(parents=True,exist_ok=True)
    trace=out/'semantic.trace'
    trace.write_text(''.join(f'{4*i:08x} {insn:08x} {4*i+4:08x} 0 {i+1:08x}\n' for i,insn in enumerate(program)),encoding='ascii')
    result=assess(trace,9,9);p=result['policies']['full0_alu1']
    assert result['adjacent_eligible']==4 and p['pairs']==3 and p['single_instructions']==3 and p['ideal_issue_groups']==6
    assert p['pair_types']=={'ALU+ALU':2,'STORE+ALU':1}
    files=[Path(__file__).resolve(),ROOT/'tools/assess_pairing.py']
    (out/'result.json').write_text(json.dumps(dict(status='PASS',checks='opcode operands, RAW/x0/WAW, RF ports, flow/recovery, greedy non-overlap',source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}),indent=2)+'\n')
    print('PASS pairing model semantic cases and greedy/non-overlap accounting')
if __name__=='__main__':main()
