"""Resolved-trace screening only; candidates must be measured in timed RTL."""
from pathlib import Path
import gzip,json
ROOT=Path(__file__).resolve().parents[1]
def screen(trace):
    rows=[]
    with gzip.open(trace,'rt') as f:
        for line in f:
            _,p,i,pr,t,a=line.split();rows.append((int(p,16),int(i,16)&127==0x63,int(a,16)))
    results={}
    for shift in (0,8,9,10,11,12,14):
      for history_bits in (0,1,2,3,4):
        entries={};wrong=misses=0;states=1<<history_bits;mask=states-1
        for pc,cond,taken in rows:
            idx=((pc>>2)^((pc>>shift) if shift else 0))&63
            e=entries.get(idx);hit=e is not None and e[0]==pc
            pred=hit and (not e[1] or e[3][e[2]]>=2)
            wrong+=pred!=taken;misses+=not hit
            if hit:
                old=e[3][e[2]];e[3][e[2]]=min(3,old+1) if taken else max(0,old-1)
                e[2]=((e[2]<<1)|taken)&mask;e[1]=cond
            else:entries[idx]=[pc,cond,taken&mask,[2 if taken else 1]*states]
        results[f'64_shift{shift}_local{history_bits}']=dict(direction_wrong=wrong,misses=misses)
    return dict(scope='Immediate resolved-history update, no speculative timing; not actual IPC',results=results)
if __name__=='__main__':
    x=screen(ROOT/'simulation/results/ipc_profile_accepted/branches.txt.gz')
    out=ROOT/'docs/ipc_opt/screening.json';out.write_text(json.dumps(x,indent=2)+'\n')
    print(json.dumps(sorted(x['results'].items(),key=lambda x:x[1]['direction_wrong']),indent=2))
