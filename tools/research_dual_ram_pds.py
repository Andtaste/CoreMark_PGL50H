"""Run identical PDS options in an isolated directory; preserve production STA."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--variant',required=True);a=ap.parse_args();assert re.fullmatch(r'[a-z_]+',a.variant)
    folder=ROOT/('simulation/results/load_bp_'+a.variant);sim=json.loads((folder/'result.json').read_text());assert sim['status']=='PASS'
    work=folder/'pds';work.mkdir(exist_ok=True);base=ROOT/'hardware/pds'
    accepted=ROOT/'docs/accepted_baseline.json';prior_report=base/'report_timing/top.rtr';preserve={p:sha(p) for p in (accepted,prior_report)}
    sources=[]
    for d in ('core','perips','sys_bus','top','source'):
      for p in sorted((base/'source'/d).glob('*.v')):
        if str(p.relative_to(ROOT)) in sim['override_sha256']:
            q=folder/p.name;assert sha(q)==sim['override_sha256'][str(p.relative_to(ROOT))];sources.append(q)
        else:sources.append(p)
    idfs=[(folder if ip!='pll' and (folder/f'ipcore/{ip}/{ip}.idf').exists() else base)/f'ipcore/{ip}/{ip}.idf' for ip in ('pll','ram1_tdp','ram2_tdp')]
    extra=[p for p in (folder/'ipcore').rglob('*.v')]+([folder/'boot64.hex'] if (folder/'boot64.hex').exists() else [])
    for n,h in sim.get('ip_sha256',{}).items():assert sha(ROOT/n)==h,n
    constraint=base/'constraints/board.fdc';inputs=sources+idfs+extra+[constraint,ROOT/'sw/build/boot.hex',Path(__file__).resolve()]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    lines=['set_arch -family Logos -device PGL50H -speedgrade -6 -package FBG484']
    lines += ['add_design {'+p.as_posix()+'}' for p in sources+idfs]
    lines += ['add_constraint {'+constraint.as_posix()+'}', 'compile -top_module top','synthesize -ads -selected_syn_tool_opt 2','dev_map',
        'pnr -max_ctrl_chain_length 4 -optimize_multi_corner_timing -fix_hold_violation -fix_hold_violation_in_route TRUE','report_timing -max_path 30 -nworst 1']
    tcl=work/'run.tcl';tcl.write_text('\n'.join(lines)+'\n')
    with (work/'build.log').open('w') as f:x=subprocess.run([r'E:\pango\PDS_2022.2-SP1-Lite\bin\pds_shell.exe','-f',str(tcl)],cwd=work,stdout=f,stderr=subprocess.STDOUT,timeout=900)
    for p,h in preserve.items():assert sha(p)==h,('Production output changed',p)
    for n,h in hashes.items():assert sha(ROOT/n)==h,n
    text=(work/'report_timing/top.rtr').read_text(errors='replace');resource=(work/'device_map/top.dmr').read_text(errors='replace')
    row=re.search(r'(\d+\.\d+) MHz\s+(\d+\.\d+) MHz',text);assert row
    corners={}
    for name in ('Setup Summary(Slow Corner)','Hold Summary(Slow Corner)','Setup Summary(Fast Corner)','Hold Summary(Fast Corner)'):
        b=text.split(name+':',1)[1].split('====',1)[0];s=re.search(r'\n\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(\d+)\s+(\d+)',b);assert s
        corners[name]=dict(worst_slack_ns=float(s[1]),failing_endpoints=int(s[3]))
    result=dict(status='PASS' if 'All Constraints Met.' in text else 'TIMING_FAILED',variant=a.variant,estimated_fmax_mhz=float(row[2]),corners=corners,
        resources={k:int(re.search(r'\| '+re.escape(k)+r'\s+\|\s+(\d+)',resource)[1]) for k in ('LUT','FF','Distributed RAM','DRM','APM')},
        input_sha256=hashes,tcl_sha256=sha(tcl),pds_exit_code=x.returncode,production_preserved=True)
    (work/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
