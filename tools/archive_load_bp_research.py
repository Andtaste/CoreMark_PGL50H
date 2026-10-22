"""Archive isolated research and prove the accepted production baseline stayed intact."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/load_bp_research'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def copy(p,q):q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
def verify(x,sub=None):
    sub=sub or {}
    for key in ('input_sha256','actual_compile_sha256'):
      for n,h in x.get(key,{}).items():assert sha(sub.get(n.replace('\\','/'),ROOT/n))==h,n
def main():
    accepted=read(ROOT/'docs/accepted_baseline.json');assert accepted==read(OUT/'accepted_baseline.json')
    for n,h in accepted['source_sha256'].items():assert sha(ROOT/n)==h,n
    assert sha(ROOT/'hardware/pds/report_timing/top.rtr')==sha(ROOT/'docs/ex_id_finish/validation/timing.rtr')
    names=('baseline','redirect_lookup','two_way','two_way_xor','both','both_xor','load_lookahead');results={}
    base=read(ROOT/'simulation/results/load_bp_baseline/result.json');basepds=read(ROOT/'simulation/results/load_bp_baseline/pds/result.json')
    assert basepds['estimated_fmax_mhz']==accepted['estimated_fmax_mhz'] and basepds['resources']==accepted['resources']
    for name in names:
        src=ROOT/('simulation/results/load_bp_'+name);dest=OUT/name;x=read(src/'result.json');assert x['status']=='PASS'
        sub={'tools/research_load_bp.py':src/'tool_snapshot.py'}
        if (src/'helper_snapshot.py').exists():sub['tools/research_load_lookahead.py']=src/'helper_snapshot.py'
        verify(x,sub)
        for n,h in x['override_sha256'].items():assert sha(src/Path(n).name)==h,n
        for k in ('Retired instructions','Retired loads','Retired stores','BJP instructions','seedcrc','[0]crclist','[0]crcmatrix','[0]crcstate','[0]crcfinal'):assert x['metrics'][k]==base['metrics'][k],(name,k)
        for p in src.iterdir():
            if p.is_file() and p.suffix in ('.json','.v','.py','.txt','.gz','.log'):copy(p,dest/p.name)
        c=int(x['metrics']['Stats window cycles']);c0=int(base['metrics']['Stats window cycles'])
        r=dict(cycles=c,ipc=int(x['metrics']['Retired instructions'])/c,predictor=x['predictor'],same_clock_speedup_percent=(c0/c-1)*100,
            source_overrides=x['override_sha256'],pds=None)
        if (src/'pds/result.json').exists():
            p=read(src/'pds/result.json');verify(p);assert p['production_preserved']
            r['pds']=p;r['estimated_peak_throughput_change_percent']=(c0/c*p['estimated_fmax_mhz']/basepds['estimated_fmax_mhz']-1)*100
            for p0,n in [(src/'pds/result.json','result.json'),(src/'pds/build.log','build.log'),(src/'pds/run.tcl','run.tcl'),
                         (src/'pds/report_timing/top.rtr','timing.rtr'),(src/'pds/device_map/top.dmr','resources.dmr')]:copy(p0,dest/'pds'/n)
        if (src/'checks/result.json').exists():
            checks=read(src/'checks/result.json');assert checks['status']=='PASS';verify(checks);r['pilot_checks']=checks['scope']
            for p in (src/'checks').iterdir():
                if p.suffix in ('.json','.log'):copy(p,dest/'checks'/p.name)
        results[name]=r
    for name in ('both_xor','load_lookahead'):
        src=ROOT/('simulation/results/load_bp_'+name+'_validation');x=read(src/'result.json');assert x['status']=='PASS';verify(x)
        for p in src.iterdir():
            if p.is_file() and p.suffix in ('.json','.v','.py','.txt','.log'):copy(p,OUT/(name+'_validation')/p.name)
    for p in (ROOT/'simulation/research').iterdir():copy(p,OUT/'research_sources'/p.name)
    for n in ('research_load_bp.py','research_load_lookahead.py','research_pds.py','screen_load_bp.py','check_load_bp_research.py','archive_load_bp_research.py'):copy(ROOT/'tools'/n,OUT/'tools'/n)
    result=dict(status='RESEARCH_ONLY_PRODUCTION_UNCHANGED',user_accepted=False,baseline=accepted,experiments=results,
        diagnosis=read(ROOT/'simulation/results/load_bp_baseline/analysis.json'),
        limits=['Same fixed CoreMark images; all altered RTL is outside hardware/pds/source.',
                'Pilot checks are not full ISA regression or board validation.',
                'PDS uses the same device/IP/constraints/options in separate directories. Baseline reproduces accepted Fmax/resources.',
                'Each variant has one PDS implementation; placement sensitivity remains.',
                'Same-clock gain is measured in RTL; peak-throughput change combines RTL cycles and estimated Fmax, not board results.',
                'Initial lookahead prototype passed Verilator but stalled in Icarus due to implicit pointer width; explicitly wrapped pointer was retested.'])
    save(OUT/'comparison.json',result)
    save(OUT/'manifest.json',dict(status='PASS',files_sha256={str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='manifest.json'}))
    print(json.dumps({k:{q:v for q,v in x.items() if q in ('cycles','ipc','same_clock_speedup_percent','estimated_peak_throughput_change_percent')} for k,x in results.items()},indent=2))
if __name__=='__main__':main()
