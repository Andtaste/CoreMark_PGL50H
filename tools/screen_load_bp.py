"""Resolved trace screening of equal-capacity BTBs, not an IPC prediction."""
from pathlib import Path
from collections import OrderedDict
import gzip,json
ROOT=Path(__file__).resolve().parents[1]
def main():
    rows=[]
    with gzip.open(ROOT/'simulation/results/load_bp_baseline/branches.txt.gz','rt') as f:
        for line in f:
            p,i,pr,t,a,d=[int(x,16) for x in line.split()];rows.append((p,i&127==0x63,t,a))
    result={}
    for ways in (1,2,4,64):
      for xor in (False,True) if ways!=64 else (False,):
        sets=64//ways;bits=sets.bit_length()-1;tables=[OrderedDict() for _ in range(sets)]
        miss=direction=target_wrong=0
        for pc,cond,target,taken in rows:
            index=((pc>>2)^((pc>>(bits+2)) if xor else 0))&(sets-1);cache=tables[index]
            e=cache.get(pc);hit=e is not None;pred=hit and (not e[0] or e[2][e[1]]>=2)
            miss+=not hit;direction+=pred!=taken;target_wrong+=bool(pred and taken and e[3]!=target)
            if hit:
                state=e[2][e[1]];e[2][e[1]]=min(3,state+1) if taken else max(0,state-1)
                e[1]=taken if cond else 0;e[0]=cond;e[3]=target;cache.move_to_end(pc)
            else:
                if len(cache)==ways:cache.popitem(last=False)
                cache[pc]=[cond,taken if cond else 0,[2 if taken else 1]*2,target]
        result[f'ways{ways}_'+('xor' if xor else 'direct')]=dict(misses=miss,direction_wrong=direction,target_wrong=target_wrong,total_wrong=direction+target_wrong)
    output=dict(scope='64 total entries, one local-history bit, two 2-bit counters, immediate resolved training, LRU replacement. No speculative timing.',results=result)
    (ROOT/'docs/load_bp_research/screening.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))
if __name__=='__main__':main()
