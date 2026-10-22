"""Same physical flow, allowing numeric suffixes in isolated trial names."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'tools/research_dual_ram_pds.py';s=base.read_text().replace("r'[a-z_]+'","r'[a-z0-9_]+'").replace("folder if ip!='pll' and",'folder if').replace('timeout=900','timeout=1800')
ns={'__file__':str(Path(__file__).resolve()),'__name__':'numbered_trial_route'};exec(compile(s,str(base),'exec'),ns);ns['main']()
