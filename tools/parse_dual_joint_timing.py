"""Parse both passing and failing PDS setup paths without hiding negative slack."""
import re
def paths(report):
 items=[]
 for part in report.read_text(errors='replace').split('Startpoint  : ')[1:31]:
  m=re.search(r'Slack \((?:MET|VIOLATED)\)\s+(-?[\d.]+)',part);d=re.search(r'Logic:\s*([\d.]+)ns.*?Route:\s*([\d.]+)ns',part)
  assert m and d,(report,part[:300])
  start=re.search(r'\btco\b',part);data=part[start.end():part.index('Data arrival time')] if start else ''
  items.append(dict(start=part.splitlines()[0].strip(),end=re.search(r'Endpoint\s+: (.+)',part)[1].strip(),slack_ns=float(m[1]),logic_ns=float(d[1]),route_ns=float(d[2]),logic_levels=int(re.search(r'Logic Levels:\s*(\d+)',part)[1]),max_data_fanout=max(map(int,re.findall(r'net \(fanout=(\d+)\)',data)),default=0)))
 return items
