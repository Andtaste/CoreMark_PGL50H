"""Verify deleted files and byte-identical protected evidence after cleanup."""
from pathlib import Path
from collections import Counter
import hashlib,json
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'new_core/docs/fpga_cleanup_execution_20261022'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 p=read(OUT/'prepared.json');x=read(OUT/'execution.json');assert x['prepared_sha256']==sha(OUT/'prepared.json')
 approved={z['path'] for z in p['approved']};counts=Counter();sizes=Counter()
 for z in x['deleted']:
  assert z['path'] in approved and not (ROOT/z['path']).exists(),z
  counts[z['category']]+=1;sizes[z['category']]+=z['bytes']
 assert len(x['deleted'])==x['deleted_files'] and sum(sizes.values())==x['deleted_logical_bytes']
 print('Checking',len(p['protected_sha256']),'protected evidence files after cleanup',flush=True)
 for name,h in p['protected_sha256'].items():assert sha(ROOT/name)==h,('Protected evidence changed',name)
 a=read(ROOT/'new_core/docs/accepted_dual_baseline.json');assert a['variant']=='dual_boundary_storewrite'
 for k in ('source_sha256','ip_sha256','evidence_sha256'):
  for name,h in a[k].items():assert sha(ROOT/'new_core'/name)==h,(k,name)
 summary=dict(status='PASS',deleted_files=x['deleted_files'],deleted_logical_bytes=x['deleted_logical_bytes'],protected_files_verified=len(p['protected_sha256']),manifest_files_preserved=p['manifests'],accepted_dual_baseline=a['variant'],counts=dict(counts),bytes=dict(sizes),execution_sha256=sha(OUT/'execution.json'),scope='Deleted entries are exact members of authorized list and absent; all protected before/after SHA hashes identical; accepted RTL/IP/evidence verified. Existing reports/checkpoints/firmware retained.')
 (OUT/'verification.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
