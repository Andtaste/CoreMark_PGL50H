"""Import ONLY vendor IP configurations and board pin constraints, then
regenerate IP for this project. No old CPU/SoC RTL is imported.
"""
from pathlib import Path
import argparse,subprocess,json,hashlib,shutil,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path)
    p.add_argument('--project',type=Path,help='PDS directory; defaults to the board5000 project when present')
    p.add_argument('--pds',type=Path,default=Path('E:/pango/PDS_2022.2-SP1-Lite'));a=p.parse_args()
    project=(a.project or (ROOT/'hardware/pds_board5000' if (ROOT/'hardware/pds_board5000').exists() else ROOT/'hardware/pds')).resolve()
    image=ROOT/'sw/build/boot.hex';assert image.is_file(),'Run build_firmware.py first'
    provenance=project/'ipcore/PROVENANCE.json'
    manifest=json.loads(provenance.read_text()) if provenance.exists() else {}
    for name in ('pll','ram1_tdp','ram2_tdp'):
        dest=project/f'ipcore/{name}/{name}.idf';dest.parent.mkdir(parents=True,exist_ok=True)
        source=dest if a.source is None and dest.exists() else (a.source or ROOT.parent/'CoreMark_PGL50H-2')/f'hardware/pds/ipcore/{name}/{name}.idf'
        origin_hash=hashlib.sha256(source.read_bytes()).hexdigest()
        tree=ET.parse(source)
        if name=='ram1_tdp':
            values={x.findtext('name'):x.findtext('value') for x in tree.findall('.//param')}
            selected=image
            if values.get('A_DATA_WIDTH')=='64' and values.get('B_DATA_WIDTH')=='32':
                memory=project/'memory';memory.mkdir(exist_ok=True)
                shutil.copyfile(image,memory/'boot.hex')
                words=[int(x,16) for x in image.read_text().split()];assert len(words)==16384
                lines=[]
                for i in range(0,len(words),2):
                    data=words[i].to_bytes(4,'little')+words[i+1].to_bytes(4,'little')
                    encoded=bytes(data[j] for j in (0,4,1,5,2,6,3,7))
                    assert bytes(encoded[j] for j in (0,2,4,6,1,3,5,7))==data
                    lines.append(encoded[::-1].hex())
                selected=memory/'boot_interleaved.hex';selected.write_text('\n'.join(lines)+'\n')
            for param in tree.findall('.//param'):
                if param.findtext('name')=='INIT_FILE':param.find('value').text=selected.as_posix()
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
    dest=project/'constraints/board.fdc';dest.parent.mkdir(parents=True,exist_ok=True)
    # Remove obsolete non-clock JTAG routing constraint; ports remain pinned.
    if not dest.exists() or a.source is not None:
        dest.write_text('\n'.join(x for x in source.read_text().splitlines() if 'PAP_CLOCK_DEDICATED_ROUTE' not in x)+'\n')
    provenance.write_text(json.dumps(manifest,indent=2))
    print('PANGO_IP_OK')
if __name__=='__main__':main()
