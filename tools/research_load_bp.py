"""Isolated experiments: all altered RTL lives under simulation/results."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,gzip,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def linux(p):
    p=Path(p).resolve();return '/mnt/'+p.drive[0].lower()+p.as_posix()[2:]
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def redirect_lookup(src):
    src=src.replace('.lookup_pc(next_pc)','.lookup_pc(redirect ? target : next_pc)')
    old='cmd_valid<=1;cmd_pc<=target;cmd_prediction<=0;cmd_stale<=0;next_pc<=target+32\'d4;'
    new='''cmd_valid<=1;cmd_pc<=target;cmd_prediction<=bp_flush ? 32'b0 : lookup_prediction;cmd_stale<=0;
     next_pc<=!bp_flush && lookup_prediction[30] ? {lookup_prediction[29:0],2'b0} : target+32'd4;'''
    assert old in src;return src.replace(old,new)
def analyze(folder,ref):
    counts=Counter();pcs=defaultdict(Counter);pairs=Counter()
    with gzip.open(folder/'branches.txt.gz','rt') as f:
      for line in f:
        p,i,pr,t,a,d=[int(x,16) for x in line.split()];bypass=d>>40;valid=(d>>39)&1;hit=(d>>38)&1
        state=(d>>32)&31;conditional=(d>>37)&1;owner=d&0xffffffff
        pred=(pr>>30)&1;wrong=pred!=a;target_wrong=pred and a and (pr&0x3fffffff)<<2!=t
        cause='correction_bypass' if bypass else 'tag_hit' if hit else 'tag_conflict' if valid else 'invalid_entry'
        counts['branches']+=1;counts[cause]+=1;counts[cause+'_direction_wrong']+=wrong
        counts['direction_wrong']+=wrong;counts['target_wrong']+=target_wrong
        c=pcs[f'{p:08x}'];c['count']+=1;c[cause]+=1;c['direction_wrong']+=wrong
        if bypass:
            would_take=hit and (not conditional or ((state>>3)&1 if state&16 else (state>>1)&1))
            counts['bypass_target_hit']+=hit;counts['bypass_direction_correctable']+=wrong and bool(would_take)==bool(a)
        elif valid and not hit:pairs[f'{p:08x} <- {owner:08x}']+=1
    assert counts['branches']==ref['predictor']['resolved']
    assert counts['direction_wrong']==ref['predictor']['direction_wrong'] and counts['target_wrong']==ref['predictor']['target_wrong']
    log=(folder/'simulation.log').read_text(errors='replace')
    age={int(i):int(v) for i,v in re.findall(r'LB_LOAD_AGE (\d+) (\d+)',log) if int(v)}
    cause={int(i):int(v) for i,v in re.findall(r'LB_LOAD_CAUSE (\d+) (\d+)',log)}
    look=re.search(r'LB_LOOKAHEAD ([^\r\n]+)',log)
    result=dict(status='PASS',branch_causes=dict(counts),by_pc=dict(sorted(pcs.items(),key=lambda x:-x[1]['direction_wrong'])),
        conflict_pairs=dict(pairs.most_common()),load_ex_to_request=age,extra_request_delay_causes=cause,
        lookahead={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',look[1])},
        notes=['Shadow metadata follows the real command/FIFO/token handshakes.',
               'Lookahead counters are structural opportunities, not guaranteed saved program cycles.',
               'Extra delay sums are per-load waiting time; concurrent loads can overlap.'])
    assert sum(age.values())==int(ref['metrics']['Retired loads'])
    assert sum(cause.values())==sum((k-1)*v for k,v in age.items())
    save(folder/'analysis.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ('by_pc','conflict_pairs')},indent=2))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=('baseline','redirect_lookup','two_way','two_way_xor','both','both_xor','load_lookahead'),default='baseline')
    ap.add_argument('--observe',action='store_true');ap.add_argument('--validation',action='store_true');a=ap.parse_args()
    assert not a.observe or a.variant=='baseline'
    out=ROOT/('simulation/results/load_bp_'+a.variant+('_validation' if a.validation else ''));out.mkdir(parents=True,exist_ok=True)
    rtl=sum([sorted((ROOT/'hardware/pds/source'/d).glob('*.v')) for d in ('core','perips','sys_bus','top')],[])
    uart_src=ROOT/'hardware/pds/source/perips/nc_uart.v';tb_src=ROOT/'simulation/tb/soc_tb.v';model=ROOT/'simulation/models/pango_ram_models.v'
    image=ROOT/('sw/build/coremark_validation_1/coremark.hex' if a.validation else 'sw/build/coremark_performance_10/coremark.hex')
    inputs=rtl+[tb_src,model,image,Path(__file__).resolve()];overrides={}
    if a.variant in ('redirect_lookup','both','both_xor'):
        p=ROOT/'hardware/pds/source/core/nc_fetch.v';q=out/'nc_fetch.v';q.write_text(redirect_lookup(p.read_text()));overrides[p]=q
    if a.variant in ('two_way','two_way_xor','both','both_xor'):
        p=ROOT/'hardware/pds/source/core/nc_btb.v';template=ROOT/'simulation/research/btb_two_way.v';q=out/'nc_btb.v'
        q.write_text(template.read_text().replace('localparam INDEX_XOR=0;','localparam INDEX_XOR=1;') if a.variant.endswith('_xor') else template.read_text());overrides[p]=q;inputs+=[template]
    if a.variant=='load_lookahead':
        from research_load_lookahead import transform
        core=ROOT/'hardware/pds/source/core/nc_core.v';fifo=ROOT/'hardware/pds/source/core/nc_fifo.v'
        c,f=transform(core.read_text(),fifo.read_text())
        for p,t in ((core,c),(fifo,f)):
            q=out/p.name;q.write_text(t);overrides[p]=q
        inputs+=[ROOT/'tools/research_load_lookahead.py']
    tb=tb_src.read_text().replace(' defparam dut.bus.uart.BAUD=9375000;','')
    if a.observe:
        obs=ROOT/'simulation/research/load_bp_observer.vh';inputs+=[obs];tb=tb.replace('endmodule',obs.read_text()+'\nendmodule')
    hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    (out/'tool_snapshot.py').write_bytes(Path(__file__).read_bytes())
    uart=out/'nc_uart_sim.v';uart.write_text(uart_src.read_text().replace('BAUD=115200','BAUD=9375000'));tb_path=out/'soc_tb_sim.v';tb_path.write_text(tb)
    actual=[overrides.get(p,p) for p in rtl if p!=uart_src]+[uart,model,tb_path]
    prefix=['wsl.exe','-d','Ubuntu','--cd',linux(ROOT),'--']
    with (out/'compile.log').open('w') as f:subprocess.run([*prefix,'verilator','--binary','--timing','-j','4','-Wno-fatal','-DCOREMARK_SIM','--top-module','soc_tb','--Mdir',linux(out/'obj'),*[linux(p) for p in actual]],stdout=f,stderr=subprocess.STDOUT,check=True)
    with (out/'simulation.log').open('w') as f:subprocess.run([*prefix,linux(out/'obj/Vsoc_tb'),f'+image={linux(image)}',f'+trace={linux(out)}/unused.trace',f'+lbtrace={linux(out)}/branches.txt',f'+uart={linux(out)}/uart.txt','+notrace=1','+limit=33000000'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
    log=(out/'simulation.log').read_text(errors='replace');uart_text=(out/'uart.txt').read_text();assert 'COUNTER_CHECK_PASS' in log and 'CRC validation   : PASS' in uart_text and 'PASS cycles=' in log
    metrics={s.split(':',1)[0].strip():s.split(':',1)[1].strip() for s in uart_text.splitlines() if ':' in s}
    ref=json.loads((ROOT/('simulation/results/coremark_validation_1_verilator_exid_final/result.json' if a.validation else 'simulation/results/coremark_performance_10_verilator_exid_aux/result.json')).read_text())
    for k in ('Retired instructions','Retired loads','Retired stores','BJP instructions','seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal'):assert metrics[k]==ref['metrics'][k],k
    if a.variant=='baseline':assert metrics==ref['metrics']
    for n,h in hashes.items():assert sha(ROOT/n)==h,n
    result=dict(status='PASS',scope='Isolated research only; production RTL, acceptance, IP and constraints unchanged',variant=a.variant,metrics=metrics,
        input_sha256=hashes,override_sha256={str(p.relative_to(ROOT)):sha(q) for p,q in overrides.items()},
        actual_compile_sha256={str(p.relative_to(ROOT)):sha(p) for p in actual},image_sha256=sha(image))
    for name,marker in (('predictor','PREDICTOR_STATS'),('multiply','MULTIPLY_STATS')):
        m=re.search(marker+r' ([^\r\n]+)',log);assert m;result[name]={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])}
    save(out/'result.json',result)
    if a.observe:
        trace=out/'branches.txt'
        with trace.open('rb') as f,gzip.open(out/'branches.txt.gz','wb') as g:
            for b in iter(lambda:f.read(1<<20),b''):g.write(b)
        analyze(out,ref);trace.unlink()
    print(json.dumps(dict(variant=a.variant,cycles=int(metrics['Stats window cycles']),ipc=int(metrics['Retired instructions'])/int(metrics['Stats window cycles']),predictor=result['predictor']),indent=2))
if __name__=='__main__':main()
