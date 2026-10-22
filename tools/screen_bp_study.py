"""Cycle-scheduled counterfactual predictors; never estimates IPC from misses.

Actual accepted-CPU lookup UIDs, old-state reads and registered training are
replayed. Changed predictions do NOT reschedule the CPU. Baseline must match
saved predictions exactly, including correction bypasses and warmup.
"""
from pathlib import Path
from collections import Counter
import gzip,hashlib,json,time
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class Predictor:
    def __init__(self,name,size=64,fold=0,upper=False,hist=1,mode='local',gh=0,ras=0):
        self.name=name;self.size=size;self.fold=fold;self.upper=upper;self.hist=hist;self.mode=mode;self.ghbits=gh;self.gh=0;self.rasdepth=ras;self.stack=[]
        self.entries=[None]*size;self.bht=[None]*256;self.snap=[None]*1024;self.count=Counter()
    def index(self,pc):
        bits=self.size.bit_length()-1;high=(pc>>(bits+2))&((1<<self.fold)-1)
        return ((pc>>2)^(high<<(bits-self.fold) if self.upper else high))&(self.size-1)
    def phtindex(self,pc):
        return ((pc>>2)^self.gh)&255 if self.mode.startswith('gshare') else ((pc>>2)^(pc>>10))&255
    def lookup(self,uid,pc,bypass):
        e=self.entries[self.index(pc)];hit=e is not None and e[0]==pc and not bypass;idx=self.phtindex(pc)
        pred=False;target=0
        if hit:
            if self.mode=='local':direction=e[4][e[3]]>=2
            else:
                state=self.bht[idx]
                direction=state is not None and (state[1][state[0]]>=2 if self.mode=='ind_local' else state>=2)
            pred=not e[2] or direction;target=self.stack[-1] if self.rasdepth and e[5] and self.stack else e[1]
        self.snap[uid&1023]=(uid,hit,pred,target,idx)
    def update(self,uid,pc,target,insn,flags):
        branch=flags&4;cond=bool(flags&2);taken=bool(flags&1);i=self.index(pc);e=self.entries[i];same=e is not None and e[0]==pc
        if not branch:
            if same:self.entries[i]=None
            return
        op=insn&127;rd=(insn>>7)&31;rs=(insn>>15)&31
        push=op in (0x6f,0x67) and rd in (1,5)
        pop=op==0x67 and rs in (1,5) and (rd not in (1,5) or rd!=rs)
        if cond and self.mode!='local':
            snap=self.snap[uid&1023];assert snap is not None and snap[0]==uid,(self.name,uid)
            idx=self.phtindex(pc) if self.mode=='gshare_current' else snap[4]
            state=self.bht[idx]
            if self.mode=='ind_local':
                if state is None:self.bht[idx]=[taken,[2 if taken else 1]*2]
                else:
                    old=state[0];state[1][old]=max(0,min(3,state[1][old]+(1 if taken else -1)));state[0]=taken
            else:self.bht[idx]=(2 if taken else 1) if state is None else max(0,min(3,state+(1 if taken else -1)))
            if self.mode.startswith('gshare'):self.gh=((self.gh<<1)|taken)&((1<<self.ghbits)-1)
        if not same:
            self.entries[i]=[pc,target,cond,int(taken) if cond else 0,[2 if taken else 1]*(1<<self.hist),pop]
        else:
            e[1]=target;e[2]=cond;e[5]=pop
            if cond:
                history=e[3];e[4][history]=max(0,min(3,e[4][history]+(1 if taken else -1)));e[3]=((history<<1)|taken)&((1<<self.hist)-1)
            else:e[3]=0
        if self.rasdepth:
            if pop and self.stack:self.stack.pop()
            if push:
                self.stack.append((pc+4)&0xffffffff)
                if len(self.stack)>self.rasdepth:self.stack.pop(0)
    def resolve(self,uid,pc,insn,target,taken,measured,saved):
        s=self.snap[uid&1023];assert s is not None and s[0]==uid,(self.name,uid)
        _,hit,pred,t,_=s
        if self.name=='baseline':
            assert hit==bool(saved>>31) and pred==bool((saved>>30)&1),(uid,hex(pc),'prediction mismatch')
            if pred:assert t==(saved&0x3fffffff)<<2,(uid,hex(pc),'target mismatch')
        if not measured:return
        c=self.count;c['resolved']+=1;c['hits']+=hit;c['predicted_taken']+=pred;c['direction_wrong']+=pred!=bool(taken)
        wrong=bool(pred and taken and t!=target);c['target_wrong']+=wrong;c['next_pc_wrong']+=(pred!=bool(taken)) or wrong
        if self.name=='baseline' and wrong:
            op=insn&127;rd=(insn>>7)&31;rs=(insn>>15)&31
            c['target_wrong_return' if op==0x67 and rs in (1,5) and (rd not in (1,5) or rd!=rs) else 'target_wrong_other']+=1
    def flush(self):self.entries=[None]*self.size;self.bht=[None]*256;self.gh=0;self.stack=[]

def main():
    models=[Predictor('baseline')]
    for fold in (1,2,3,4,6):models.append(Predictor(f'fold{fold}',fold=fold))
    for fold in (2,3,4):models.append(Predictor(f'fold{fold}_upper',fold=fold,upper=True))
    models.extend([Predictor('direct128',size=128),Predictor('fold128',size=128,fold=7)])
    for h in (2,3):
        models.append(Predictor(f'local{h}',hist=h))
        for fold in (2,3,4):models.append(Predictor(f'fold{fold}_local{h}',fold=fold,hist=h))
    for gh in (4,6,8):models.append(Predictor(f'gshare{gh}_saved',mode='gshare_saved',gh=gh))
    models.extend([Predictor('gshare6_current',mode='gshare_current',gh=6),Predictor('ind_bimodal',mode='bimodal'),Predictor('ind_local1',mode='ind_local')])
    for depth in (4,8):models.append(Predictor(f'ras{depth}',ras=depth))
    folder=ROOT/'simulation/results/bp_study_trace';trace=folder/'events.txt.gz';ref=json.loads((folder/'result.json').read_text())
    start=time.time();lines=0;last_flush=-1
    with gzip.open(trace,'rt') as f:
        for line in f:
            fields=line.split();kind=fields[0];values=[int(s,16) for s in fields[1:]];edge=values[0];lines+=1
            if kind in ('P','C'):
                _,uid,pc=values
                for m in models:m.lookup(uid,pc,kind=='C')
            elif kind=='U':
                if edge!=last_flush:
                    _,uid,pc,target,insn,flags=values
                    for m in models:m.update(uid,pc,target,insn,flags)
            elif kind=='X':
                _,uid,pc,insn,target,taken,measured,saved=values
                for m in models:m.resolve(uid,pc,insn,target,taken,measured,saved)
            elif kind=='F':
                last_flush=edge
                for m in models:m.flush()
            else:raise AssertionError(kind)
            if lines%1000000==0:print('screened events',lines,'seconds',round(time.time()-start,1),flush=True)
    baseline=models[0].count
    for k in ('resolved','hits','predicted_taken','direction_wrong','target_wrong','next_pc_wrong'):assert baseline[k]==ref['predictor'][k],(k,baseline[k],ref['predictor'][k])
    result=dict(status='PASS',scope='Fixed real lookup/training schedule, old-state semantics, full warmup, actual UID binding; not rescheduled CPU or IPC prediction',
        trace_sha256=sha(trace),collector_result_sha256=sha(folder/'result.json'),tool_sha256=sha(Path(__file__)),events=lines,
        results={m.name:dict(m.count) for m in models},limits=['Changed predictions do not change fetch/EX timing in this replay.',
            'gshare*_saved needs lookup-index metadata through fetch/ID/EX and registered training.',
            'gshare*_current deliberately trains using current resolved history; it is a separate cheaper design.',
            'RAS is resolved-only, no speculative push/pop or rollback. All models retain correction bypass.'])
    out=ROOT/'docs/bp_study';out.mkdir(parents=True,exist_ok=True);(out/'screening.json').write_text(json.dumps(result,indent=2)+'\n')
    for m in sorted(models,key=lambda m:m.count['next_pc_wrong']):print(m.name,dict(m.count))
if __name__=='__main__':main()
