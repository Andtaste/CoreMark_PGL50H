"""Check the actual PDS routed report for board pins and all-corner timing."""
from pathlib import Path
import argparse, hashlib, json, re

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inspect(project, expected_mhz=82):
    project = Path(project)
    fdc = (project/'constraints/board.fdc').read_text()
    locations = dict(re.findall(r'define_attribute \{p:(.*?)\} \{PAP_IO_LOC\} \{(.*?)\}',fdc))
    standards = dict(re.findall(r'define_attribute \{p:(.*?)\} \{PAP_IO_STANDARD\} \{(.*?)\}',fdc))
    prr = project/'place_route/top.prr'
    prr_text = prr.read_text(errors='replace')
    lines = prr_text.splitlines()
    header = next(line for line in lines if line.startswith('| PORT '))
    columns = [v.strip() for v in header.split('|')[1:]]
    pins = {}
    for line in lines:
        if not line.startswith('|'):
            continue
        row = dict(zip(columns,[v.strip() for v in line.split('|')[1:]]))
        port = row.get('PORT')
        if port in locations:
            assert row['LOC'] == locations[port], f'{port}: actual {row["LOC"]}, expected {locations[port]}'
            assert row['CONSTRAINT'] == 'YES', f'{port}: board constraint was not applied'
            assert row['IOSTANDARD'] == standards[port], f'{port}: I/O standard mismatch'
            pins[port] = {'location':row['LOC'],'iostandard':row['IOSTANDARD'],'constraint_applied':True}
    for port in ('clk','rst_ext_i','uart_tx_pin','halted_ind','gpio[0]','gpio[1]','jtag_TDO'):
        assert port in pins, f'Missing active board port: {port}'
    report = project/'report_timing/top.rtr'
    data = report.read_text(errors='replace')
    match = re.search(r'(\d+\.\d+) MHz\s+(\d+\.\d+) MHz',data)
    assert match and abs(float(match[1])-expected_mhz)<0.01, f'Expected actual {expected_mhz} MHz clock constraint'
    assert 'All Constraints Met.' in data, 'Timing constraints violated'
    corners = {}
    for name in ('Setup Summary(Slow Corner)','Hold Summary(Slow Corner)',
                 'Setup Summary(Fast Corner)','Hold Summary(Fast Corner)'):
        block = data.split(name+':',1)[1].split('====',1)[0]
        value = re.search(r'\n\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(\d+)\s+(\d+)',block)
        assert value and float(value[1]) >= 0 and int(value[3]) == 0, name
        corners[name] = {'worst_slack_ns':float(value[1]),'failing_endpoints':int(value[3])}
    resources = {}
    for label in ('LUT','FF','Distributed RAM'):
        resources[label] = sum(map(int,re.findall(r'^\|\s+'+label+r'\s+\|\s+(\d+)',prr_text,re.M)))
    for label in ('DRM','APM'):
        resources[label] = int(re.search(r'^\| Use of '+label+r'\s+\|\s+(\d+)',prr_text,re.M)[1])
    return dict(status='PASS',requested_mhz=float(match[1]),estimated_fmax_mhz=float(match[2]),
                corners=corners,board_pins=pins,sta_sha256=sha(report),pnr_report_sha256=sha(prr),
                routed_db_sha256=sha(project/'place_route/top_pnr.adf'),routed_resources=resources)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--expected-mhz',type=float,default=82)
    args = parser.parse_args()
    result = inspect(args.project,args.expected_mhz)
    if args.output:
        args.output.write_text(json.dumps(result,indent=2)+'\n')
    print('PASS actual routed board pins and all-corner timing')

if __name__ == '__main__':
    main()
