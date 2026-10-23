"""Prove both transformed incoming expressions against exact parent RTL."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
trial=ROOT/'simulation/results/autonomous_20261022/incoming_side_masks'
meta=json.loads((trial/'parent_baseline.json').read_text())
parent=ROOT/meta['project_directory']/'source/core/nc_operands.v'
candidate=trial/'source/core/nc_operands.v'
out=trial/'incoming_proof';out.mkdir(exist_ok=True)
gold=parent.read_text();new=candidate.read_text()
ports=['input wire wait_c,wait_d','input wire[3:0] tag_c,tag_d','input wire[223:0] in_side']
for source in ('f','f1','m','w','w1'):
 ports.extend([f'input wire {source}_valid',f'input wire[3:0] {source}_tag',f'input wire[31:0] {source}_data'])
ports.append('output wire equal')
lines=['module miter('+','.join(ports)+');']
for lane in ('c','d'):
 old=re.search(r' wire\[31:0\] incoming_'+lane+r'=[^\n]+',gold)[0]
 lines.append(old.replace('incoming_'+lane,'gold_'+lane))
 start=new.index(' wire inc_'+lane+'_hit_f=')
 end=new.index('\n',new.index(' wire[31:0] incoming_'+lane+'=',start))
 lines.append(new[start:end])
lines.extend(['assign equal=(gold_c==incoming_c) && (gold_d==incoming_d);','endmodule'])
bench=out/'miter.v';bench.write_text('\n'.join(lines)+'\n')
linux='/mnt/'+bench.drive[0].lower()+bench.as_posix()[2:]
script=f'read_verilog {linux}; prep -top miter; sat -verify -prove equal 1 -show-inputs'
r=subprocess.run(['wsl.exe','-d','Ubuntu','--','yosys','-p',script],capture_output=True,timeout=120)
(out/'yosys.log').write_bytes(r.stdout+r.stderr)
assert r.returncode==0 and b'SUCCESS!' in r.stdout,r.stdout[-2000:]
(out/'result.json').write_text(json.dumps(dict(status='PASS',scope='Combinational equivalence of exact incoming C/D expressions for arbitrary two-state data, tags, valid and wait; including simultaneous hits and original priority',input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [parent,candidate,bench,Path(__file__)]}),indent=2)+'\n')
print('PASS incoming C/D arbitrary-input SAT equivalence')
