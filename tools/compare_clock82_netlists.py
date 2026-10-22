"""Compare complete structural netlists, allowing only inferred RAM replica renaming."""
from pathlib import Path
import re,json,hashlib,collections
ROOT=Path(__file__).resolve().parents[1]
def compare(a,b):
 def read(p):
  text=re.sub(r'/\*.*?\*/|//[^\n]*','',p.read_text(errors='replace'),flags=re.S)
  assert not re.search(r'\b(always|initial|function|task|generate)\b',text),'Requires structural-only netlists'
  modules={}
  for block in re.findall(r'\bmodule\b(.*?)\bendmodule\b',text,re.S):
   name=re.match(r'\s*(\w+)',block)[1];assert name not in modules
   modules[name]=[re.sub(r'\s+','',s) for s in block.split(';')]
  assert len(modules)==25,len(modules)
  return text,modules
 ta,ma=read(a);tb,mb=read(b);assert set(ma)==set(mb)
 differences=[n for n in ma if collections.Counter(ma[n])!=collections.Counter(mb[n])]
 assert set(differences)<= {'nc_regfile'},differences
 replicas=[]
 for m in (ma,mb):
  signatures={};new=[]
  for s in m['nc_regfile']:
   match=re.search(r'(?<=\))(bank1(?:_\d+)*)\(',s)
   if match:
    assert 'GTP_RAM32X1DP#(' in s and '.INIT(' in s,s
    normalized=s[:match.start(1)]+'__RAM_REPLICA__'+s[match.end(1):]
    assert normalized not in signatures,'Replica signature must be unique'
    signatures[normalized]=match[1];new.append(normalized)
   else:new.append(s)
  assert len(signatures)==128,len(signatures)
  m['nc_regfile']=new;replicas.append(signatures)
 assert set(replicas[0])==set(replicas[1]),'RAM primitive type, parameters, port signals or bit lanes differ'
 assert all(collections.Counter(ma[n])==collections.Counter(mb[n]) for n in ma),'Whole structural connectivity differs'
 rename={replicas[0][s]:replicas[1][s] for s in replicas[0] if replicas[0][s]!=replicas[1][s]}
 digest=hashlib.sha256(json.dumps({n:sorted(collections.Counter(ma[n]).items()) for n in sorted(ma)},sort_keys=True).encode()).hexdigest()
 return dict(status='PASS',module_count=25,structural_statements=sum(len(x) for x in ma.values()),original_textual_equal=re.sub(r'\s+','',ta)==re.sub(r'\s+','',tb),different_modules_before_replica_name_normalization=differences,ram_replicas_checked=128,renamed_replicas=rename,canonical_sha256=digest,scope='Exact multiset equality of every structural statement in all25 modules, preserving port/parameter/wire/bit-lane expressions and duplicate counts. Only names of128 bank1 RAM32X1DP read replicas may be bijectively renamed; complete primitive parameters and connections must match.')
if __name__=='__main__':
 a=ROOT/'hardware/pds82_seed_sweep/synthesize/top_syn.vm';b=ROOT/'hardware/pds/synthesize/top_syn.vm';x=compare(a,b)
 x.update(input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (a,b,Path(__file__).resolve())})
 (ROOT/'docs/clock82_multiseed_20261022/main_netlist_equivalence.json').write_text(json.dumps(x,indent=2)+'\n');print('PASS complete structural netlists, only',len(x['renamed_replicas']),'RAM replica names permuted')
