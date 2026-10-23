"""Advisory allocation-policy model using a newly measured resolved trace."""
from pathlib import Path
import hashlib,json,sys
import profile_btb_hashes as capture
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'simulation/results/autonomous_20261022/btb_allocation_profile_shortmul'

def main():
 # Reuse the existing trace instrumentation and its independent CRC/counter
 # checks. Its original hash ranking is preserved as a cross-check only.
 capture.OUT=OUT
 capture.main()
 raw=OUT/'btb_events.trace'
 events=[]
 for line in raw.read_text().splitlines():
  if line=='F':events.append(None);continue
  v=line.split();events.append((int(v[0],16),int(v[1],16),*[int(x) for x in v[2:]]))
 results=[]
 policies={'weak_outcome':(1,2),'strong_outcome':(0,3),'weak_not_taken':(1,1),'weak_taken':(2,2),'strong_not_taken':(0,0),'strong_taken':(3,3)}
 for name,(initial_nt,initial_t) in policies.items():
  table=[None]*64;wrong=count=allocations=0
  for event in events:
   if event is None:table=[None]*64;continue
   pc,target,branch,conditional,taken,measured=event
   index=(((pc>>3)^(pc>>10))&31)*2+((pc>>2)&1)
   entry=table[index];hit=entry is not None and entry[0]==pc
   if branch:
    predicted=hit and (not entry[2] or entry[4+entry[3]]>=2)
    predicted_next=entry[1] if predicted else (pc+4)&0xffffffff
    actual_next=target if taken else (pc+4)&0xffffffff
    if measured:count+=1;wrong+=predicted_next!=actual_next;allocations+=not hit
    if not conditional:table[index]=[pc,target,0,0,3,3]
    elif not hit:
     initial=initial_t if taken else initial_nt
     table[index]=[pc,target,1,taken,initial,initial]
    else:
     pos=4+entry[3];entry[pos]=min(3,entry[pos]+1) if taken else max(0,entry[pos]-1)
     entry[1]=target;entry[2]=1;entry[3]=taken
   elif hit:table[index]=None
  results.append(dict(policy=name,next_pc_wrong=wrong,branches=count,allocations=allocations))
 original=json.loads((OUT/'result.json').read_text())
 expected=next(r for r in original['ranking'] if r['shift']==10 and r['rotate']==0)['next_pc_wrong']
 assert results[0]['next_pc_wrong']==expected
 record=dict(status='PASS',scope='Advisory resolved sequential trace; ignores fetch/training latency, not an RTL performance result',baseline=original['baseline'],benchmark_cycles=original['benchmark_cycles'],trace_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),ranking=sorted(results,key=lambda r:r['next_pc_wrong']))
 (OUT/'allocation_result.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps(record['ranking'],indent=2))

if __name__=='__main__':main()
