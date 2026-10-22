"""Import ONLY vendor IP configurations and board pin constraints, then
regenerate IP for this project. No old CPU/SoC RTL is imported.
"""
from pathlib import Path
import argparse,subprocess,json,hashlib,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path)
    p.add_argument('--pds',type=Path,default=Path('E:/pango/PDS_2022.2-SP1-Lite'));a=p.parse_args()
    image=ROOT/'sw/build/boot.hex';assert image.is_file(),'Run build_firmware.py first'
    provenance=ROOT/'hardware/pds/ipcore/PROVENANCE.json'
    manifest=json.loads(provenance.read_text()) if provenance.exists() else {}
    for name in ('pll','ram1_tdp','ram2_tdp'):
        dest=ROOT/f'hardware/pds/ipcore/{name}/{name}.idf';dest.parent.mkdir(parents=True,exist_ok=True)
        source=dest if a.source is None and dest.exists() else (a.source or ROOT.parent/'CoreMark_PGL50H-2')/f'hardware/pds/ipcore/{name}/{name}.idf'
        origin_hash=hashlib.sha256(source.read_bytes()).hexdigest()
        tree=ET.parse(source)
        if name=='ram1_tdp':
            for param in tree.findall('.//param'):
                if param.findtext('name')=='INIT_FILE':param.find('value').text=image.as_posix()
        tree.write(dest,encoding='utf-8',xml_declaration=True)
        log=dest.parent/'regenerate.log'
        with log.open('wb') as stream:
            result=subprocess.run([str(a.pds/'bin/ip_generate.exe'),'-i',str(dest),'-disable-syn'],
                                  cwd=dest.parent,stdout=stream,stderr=subprocess.STDOUT,timeout=180)
        assert result.returncode==0,log.read_text(errors='replace')[-3000:]
        if name not in manifest or a.source is not None:
            manifest[name]={'origin':str(source),'origin_sha256':origin_hash,
                            'local':str(dest.relative_to(ROOT)),'regenerated':True}
    source=(a.source or ROOT.parent/'CoreMark_PGL50H-2')/'hardware/pds/constraints/tinydram.fdc'
    dest=ROOT/'hardware/pds/constraints/board.fdc';dest.parent.mkdir(parents=True,exist_ok=True)
    # Remove obsolete non-clock JTAG routing constraint; ports remain pinned.
    if not dest.exists() or a.source is not None:
        dest.write_text('\n'.join(x for x in source.read_text().splitlines() if 'PAP_CLOCK_DEDICATED_ROUTE' not in x)+'\n')
    (ROOT/'hardware/pds/ipcore/PROVENANCE.json').write_text(json.dumps(manifest,indent=2))
    print('PANGO_IP_OK')
if __name__=='__main__':main()
