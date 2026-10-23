"""Two targeted follow-ups, reusing the hash-checked accepted RTL simulator."""
import json
import run_compiler_profiles as cp
def main():
 out=cp.OUT;original=json.loads((out/'result.json').read_text())
 for n,h in original['compiled_sha256'].items():assert cp.sha(cp.ROOT/n)==h,n
 cp.PROFILES.update(o3_inline80=['-O3','--param=max-inline-insns-auto=80'],o3_align8=['-O3','-falign-functions=8','-falign-jumps=8','-falign-loops=8'])
 prefix=['wsl.exe','-d','Ubuntu','--cd',cp.linux(cp.ROOT),'--'];rows=[]
 def evaluate(profile,count=10,validation=False):
  image=cp.build(profile,count,validation);label=profile+('_validation' if validation else '_'+str(count))
  text=cp.run([*prefix,cp.linux(out/'obj/Vsoc_tb'),'+image='+cp.linux(image),'+trace='+cp.linux(out/(label+'.trace')),'+uart='+cp.linux(out/(label+'.uart')),'+notrace=1','+limit=100000000'],out/(label+'.log'))
  printed=(out/(label+'.uart')).read_text();assert 'CRC validation   : PASS' in printed and 'COUNTER_CHECK_PASS' in text and 'PASS cycles=' in text
  metrics={s.split(':',1)[0].strip():s.split(':',1)[1].strip() for s in printed.splitlines() if ':' in s}
  if count==100:ref=json.loads((out/'longer_comparison.json').read_text())['runs'][0]['metrics']
  else:ref=json.loads((out/('o3_validation.json' if validation else 'baseline_10.json')).read_text())['metrics']
  for k in ('seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal'):assert metrics[k]==ref[k],(label,k)
  row=dict(status='PASS',profile=profile,count=count,validation=validation,metrics=metrics,cycles=int(metrics['Benchmark cycles64']),image=str(image.relative_to(cp.ROOT)),image_sha256=cp.sha(image),build=json.loads(image.with_name('build.json').read_text()))
  (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');print('EXTRA_COMPILER',label,row['cycles'],flush=True);return row
 for profile in ('o3_inline80','o3_align8'):rows.append(evaluate(profile))
 best=min(rows,key=lambda x:x['cycles']);prior=json.loads((out/'o3_10.json').read_text())
 if best['cycles']<prior['cycles']:
  evaluate(best['profile'],1,True);evaluate(best['profile'],100)
 result=dict(status='PASS',profiles=rows,best=best['profile'] if best['cycles']<prior['cycles'] else 'o3',scope='Same hash-checked RTL simulator; no firmware installation; compare same-count CRC and counters.')
 (out/'extra_result.json').write_text(json.dumps(result,indent=2)+'\n')
 print('EXTRA_COMPLETE',result['best'],flush=True)
if __name__=='__main__':main()
