"""Necessary host protocol/search checks for the shared-workspace platform."""
from pathlib import Path
import hashlib,json,queue,subprocess,threading,time
N=Path(__file__).resolve().parents[1];O=N/'simulation/results/board_games';O.mkdir(parents=True,exist_ok=True)
def main():
 p=subprocess.Popen([str(N/'sw/build/board_games/board_games_host.exe')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
 q=queue.Queue();trace=[];infos=[]
 def reader():
  for s in p.stdout:
   s=s.strip()
   if s:q.put(s)
 threading.Thread(target=reader,daemon=True).start()
 def until(prefix,timeout=30):
  lines=[];stop=time.monotonic()+timeout
  while time.monotonic()<stop:
   s=q.get(timeout=max(.01,stop-time.monotonic()));trace.append(s);lines.append(s)
   if s.startswith(prefix):return lines
  raise AssertionError(prefix)
 def send(s):p.stdin.write(s+'\n');p.stdin.flush()
 def board(s):send(s);return until('END_BOARD')
 def setting(s):send(s);until('OK '+s.split()[0])
 def search():
  lines=board('GO');info=next(s for s in lines if s.startswith('INFO '));infos.append(info)
  return info,next(s for s in lines if s.startswith('MOVE '))
 try:
  until('MENU ')
  b=board('SELECT GOMOKU');assert 'BOARD 1 0 0' in b
  before=board('SHOW')
  for cmd in ['COREMARK 6000','COREMARK 6000 VALIDATION']:
   send(cmd);cm=until('COREMARK END',60)
   assert 'CRC validation   : PASS' in cm and cm[-1]=='COREMARK END crc=PASS valid=NO_HOST_TEST'
  assert board('SHOW')==before,'CoreMark changed host game'
  send('COREMARK 0');assert until('ERROR COREMARK_ARGS')[-1]=='ERROR COREMARK_ARGS'

  board('PLAY 7 7');setting('TIME 10000');setting('DEPTH 2');setting('LIMIT 0')
  g1,m=search();assert 'nodes=97 ' in g1 and 'score=-3520 ' in g1 and m=='MOVE 2 7 6 AI',(g1,m)
  b=board('UNDO 1');assert 'BOARD 2 0 1' in b
  b=board('SELECT XIANGQI');assert 'BOARD 0 0 0 0' in b
  setting('DEPTH 2');x,m=search();assert 'nodes=909 ' in x and 'score=3 ' in x and m=='MOVE 0 82 65 AI',(x,m)
  board('UNDO 1')
  b=board('FEN 4k4/9/9/9/4P4/9/9/4c4/4P4/4K4 w');assert 'BOARD 0 0 0 1' in b
  board('PLAY 85 84');b=board('UNDO 1');assert 'BOARD 0 0 0 1' in b
  send('FEN nonsense');assert until('ERROR FEN')[-1]=='ERROR FEN'
  b=board('SELECT GOMOKU');assert 'BOARD 1 0 0' in b
  before=board('SHOW')
  for cmd in ['COREMARK 6000','COREMARK 6000 VALIDATION']:
   send(cmd);cm=until('COREMARK END',60)
   assert 'CRC validation   : PASS' in cm and cm[-1]=='COREMARK END crc=PASS valid=NO_HOST_TEST'
  assert board('SHOW')==before,'CoreMark changed host game'
  send('COREMARK 0');assert until('ERROR COREMARK_ARGS')[-1]=='ERROR COREMARK_ARGS'

  board('PLAY 7 7');setting('DEPTH 2');g2,m=search();assert 'nodes=97 ' in g2 and 'score=-3520 ' in g2 and m=='MOVE 2 7 6 AI'
  setting('DEPTH 19');send('GO');send('STOP');lines=until('END_BOARD');assert 'CANCELLED' in lines and not any(s.startswith('MOVE ') for s in lines)
  setting('DEPTH 2');before=board('SHOW');hint=board('HINT');assert any(s.startswith('HINT 1 ') for s in hint) and not any(s.startswith('MOVE ') for s in hint)
  assert hint[hint.index(next(s for s in hint if s.startswith('BOARD '))):]==before[before.index(next(s for s in before if s.startswith('BOARD '))):],'Gomoku hint changed board'
  board('SELECT XIANGQI');setting('DEPTH 2');before=board('SHOW');hint=board('HINT');assert 'HINT 0 82 65' in hint and not any(s.startswith('MOVE ') for s in hint)
  assert hint[hint.index(next(s for s in hint if s.startswith('BOARD '))):]==before[before.index(next(s for s in before if s.startswith('BOARD '))):],'Xiangqi hint changed board'
  setting('DEPTH 32');send('HINT');send('STOP');hint=until('END_BOARD');assert 'CANCELLED' in hint and not any(s.startswith(('HINT ','MOVE ')) for s in hint)
  send('MENU');until('MENU ');send('SHOW');assert until('ERROR SELECT_GAME')[-1]=='ERROR SELECT_GAME'
  p.stdin.close();assert p.wait(timeout=10)==0
  (O/'host_result.json').write_text(json.dumps(dict(status='HOST_PROTOCOL_SEARCH_SWITCH_PASS',host_executable_sha256=hashlib.sha256((N/'sw/build/board_games/board_games_host.exe').read_bytes()).hexdigest(),searches=infos,checks=['CoreMark6000 performance+validation seeds; game preserved; host scores not valid','both fixed searches','Gomoku->Xiangqi->Gomoku workspace reuse','undo','cannon FEN/check/undo','malformed FEN','STOP cancellation','non-mutating HINT both games','cancel HINT','menu/no game'],limitations='Software engines on PC;hardware-backed equivalence still required'),indent=2))
  print('PASS: host protocol,both engines,work-area reuse,cancel,undo,cannon rules and menu')
 finally:
  (O/'host_console.txt').write_text('\n'.join(trace)+'\n')
  if p.poll() is None:p.kill();p.wait()
if __name__=='__main__':main()
