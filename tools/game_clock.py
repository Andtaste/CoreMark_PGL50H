"""Explicit Logos PLL profile + generated-RTL/SDC checks for the 70MHz apps.

ip_generate consumes saved dividers; changing REQ_FREQ alone does NOT calculate them.
Pango ipml_pll/ui.tcl permits a 600..1250MHz VCO. This profile uses 700MHz.
"""
from pathlib import Path
import json,re,xml.etree.ElementTree as ET

def configure_cpu_pll(path):
 tree=ET.parse(path)
 profile={'CLKIN_FREQ':'50.0000','STATIC_RATIOI':'1','STATIC_RATIOF':'14',
          'STATIC_RATIO0':'10','STATIC_RATIOM':'1','STATIC_DUTY0':'10',
          'STATIC_DUTYF':'14','FBMODE':'false','VCODIV2_ENABLE':'false',
          'DYNAMIC_RATIOI_EN':'false','DYNAMIC_RATIOF_EN':'false',
          'DYNAMIC_RATIO0_EN':'false','DYNAMIC_RATIOM_EN':'false'}
 for item in tree.findall('.//param'):
  key=item.findtext('name')
  if key=='CLKOUT0_REQ_FREQ_basicPage':item.find('value').text='70.0000'
  for page in ('basicPage','advancedPage'):
   for name,value in profile.items():
    if key==name+'_'+page:item.find('value').text=value
 tree.write(path,encoding='utf-8',xml_declaration=True)

def static_clocks(path):
 t=Path(path).read_text()
 def number(name):
  m=re.search(r'localparam(?:\s+(?:integer|real))?\s+'+name+r'\s*=\s*([0-9.]+)\s*;',t)
  if not m:raise ValueError(f'Missing numeric PLL constant: {name}')
  return float(m.group(1))
 assert re.search(r'localparam\s+FBMODE\s*=\s*"FALSE"',t),'Only static internal-feedback profile is supported'
 for n in ('I','F','0'):
  assert re.search(r'localparam\s+DYNAMIC_RATIO'+n+r'_EN\s*=\s*"FALSE"',t),'Dynamic PLL profile unsupported'
 assert re.search(r'localparam\s+VCOCLK_DIV2\s*=\s*1\x27b0',t)
 ref=number('CLKIN_FREQ')*1e6;i=number('STATIC_RATIOI');f=number('STATIC_RATIOF');m=number('STATIC_RATIOM')
 vco=ref*m*f/i
 assert 600e6<=vco<=1250e6, f'Illegal VCO {vco}'
 return {'reference_hz':ref,'input_divider':i,'feedback_divider':f,'vco_hz':vco,
         'out0_hz':vco/number('STATIC_RATIO0'),'out1_hz':vco/number('STATIC_RATIO1')}

def verify_clocks(project):
 p=Path(project);cpu=static_clocks(p/'ipcore/pll/pll.v');video=static_clocks(p/'ipcore/video_pll/video_pll.v')
 assert abs(cpu['out0_hz']-70000000)<1, f"PLL is {cpu['out0_hz']}Hz, CPU/UART expect 70000000Hz; regenerate IP with saved dividers"
 top=(p/'source/top/game_top.v').read_text()
 assert re.search(r'\.CLOCK_HZ\(70000000\)',top)
 sdc=(p/'constraints/board.fdc').read_text()
 for domain,hz in [('cpu_domain',cpu['out0_hz']),('pixel_domain',video['out0_hz']),('cfg_domain',video['out1_hz'])]:
  match=re.search(r'create_clock -name '+domain+r' -period ([0-9.]+)',sdc);assert match,domain
  constraint=float(match.group(1));period=1e9/hz
  assert constraint<=period+0.000001 and abs(period-constraint)/period<0.001, (domain,constraint,period)
 div=(70000000+115200//2)//115200
 record={'cpu':cpu,'video':video,'uart_divider':div,'actual_baud':cpu['out0_hz']/div,
         'baud_error_percent':100*(cpu['out0_hz']/div/115200-1)}
 (p/'clock_validation.json').write_text(json.dumps(record,indent=2))
 return record

def simulate_clock_uart(project,run):
 p=Path(project);root=p.parents[1];out=root/'simulation/results/game_clock_fix_20261025'/p.name
 out.mkdir(parents=True,exist_ok=True)
 iv=root.parent/'tmp/iverilog-portable/bin/iverilog.exe'
 run([iv,'-g2012','-s','game_clock_uart_tb','-o',out/'clock.vvp',
      root/'simulation/tb/game_clock_uart_tb.v',p/'ipcore/pll/pll.v',p/'source/perips/nc_uart.v',
      'E:/pango/PDS_2022.2-SP1-Lite/arch/vendor/pango/verilog/simulation/GTP_PLL_E3.v'],log=out/'compile.log')
 log=run([iv.with_name('vvp.exe'),out/'clock.vvp'],log=out/'clock.log')
 assert 'PASS:' in log,log
 return log
