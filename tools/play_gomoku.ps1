param([string]$Port,[switch]$Local,[switch]$ListPorts,[switch]$SelfTest,[switch]$UiTest,[string]$Preview,[string]$ReplayLog,[string]$Review)
$ErrorActionPreference='Stop'
if (-not ('System.IO.Ports.SerialPort' -as [type])) { Add-Type -AssemblyName System.IO.Ports }
if ($ListPorts) {
 $ports=@([System.IO.Ports.SerialPort]::GetPortNames() | Sort-Object)
 if ($ports.Count) { $ports } else { 'No serial ports detected. Check the board USB cable and serial driver.' }
 exit 0
}
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$root=Split-Path $PSScriptRoot -Parent
$hostExe=Join-Path $root 'sw/build/gomoku/gomoku_host.exe'
if (-not ($Port -or $Local -or $SelfTest -or $UiTest -or $Preview -or $Review)) { throw 'Use -Port COM3, -ListPorts, or -Local for an explicitly labelled PC-only test.' }
$code=@'
using System;
using System.IO;
using System.IO.Ports;
using System.Diagnostics;
using System.Collections.Generic;
using System.Collections.Concurrent;
using System.Drawing;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows.Forms;

public sealed class GomokuModel {
 public byte[,] Board=new byte[15,15];
 byte[,] incoming;int rows,inSide,inWinner,inCount;
 public int Side=1,Winner,Count;
 public readonly List<Point> Moves=new List<Point>();
 public string Info="No completed search yet.";
 public bool Feed(string line) {
  line=line.Trim();if(line.Length==0)return false;
  string[] a=line.Split(new char[]{' '},StringSplitOptions.RemoveEmptyEntries);
  if(incoming!=null && rows<15) {
   if(line.Length!=15)throw new Exception("Incomplete board response. Press New to resync.");
   for(int x=0;x<15;x++){if(line[x]<'0'||line[x]>'2')throw new Exception("Invalid board data");incoming[x,rows]=(byte)(line[x]-'0');}rows++;return false;
  }
  if(a[0]=="BOARD" && a.Length==4){inSide=int.Parse(a[1]);inWinner=int.Parse(a[2]);inCount=int.Parse(a[3]);incoming=new byte[15,15];rows=0;return false;}
  if(a[0]=="END_BOARD"){
   if(incoming==null||rows!=15)throw new Exception("Missing board rows");
   int black=0,white=0;for(int y=0;y<15;y++)for(int x=0;x<15;x++){black+=incoming[x,y]==1?1:0;white+=incoming[x,y]==2?1:0;}
   if(black+white!=inCount || !(black==white||black==white+1) || inSide!=(black==white?1:2) || inWinner<0 || inWinner>2)throw new Exception("Board count/turn mismatch");
   if(Moves.Count!=inCount)throw new Exception("Board/history count mismatch");
   for(int i=0;i<Moves.Count;i++){Point p=Moves[i];if(incoming[p.X,p.Y]!=i%2+1)throw new Exception("Board/history stone mismatch");}
   Board=incoming;incoming=null;Side=inSide;Winner=inWinner;Count=inCount;return true;
  }
  if(line=="OK NEW"){Moves.Clear();return false;}
  if(a[0]=="MOVE" && a.Length==5){int x=int.Parse(a[2]),y=int.Parse(a[3]);if(x<0||x>14||y<0||y>14)throw new Exception("Move out of range");Moves.Add(new Point(x,y));}
  if(a.Length==3 && a[0]=="OK" && a[1]=="UNDO"){int n=int.Parse(a[2]);if(n>Moves.Count)throw new Exception("History mismatch");Moves.RemoveRange(Moves.Count-n,n);}
  if(a[0]=="INFO")Info=line;
  return false;
 }
 public string Replay(int who,string budget){return EncodeReplay(Moves,who,budget);}
 public static string EncodeReplay(IEnumerable<Point> moves,int who,string budget){StringBuilder s=new StringBuilder("GOMOKU1 15 FREESTYLE\nHUMAN "+who+"\nTIME "+budget+"\n");foreach(Point p in moves)s.AppendLine("MOVE "+p.X+" "+p.Y);return s.ToString();}
 public static Queue<Point> ParseReplay(string[] lines,out int who,out int budget){
  if(lines.Length<3||lines[0]!="GOMOKU1 15 FREESTYLE"||!lines[1].StartsWith("HUMAN ")||!lines[2].StartsWith("TIME "))throw new Exception("Unsupported replay format");
  who=int.Parse(lines[1].Substring(6));budget=int.Parse(lines[2].Substring(5));if(who<1||who>2||budget<50||budget>10000)throw new Exception("Invalid replay settings");
  Queue<Point> q=new Queue<Point>();bool[,] used=new bool[15,15];
  for(int i=3;i<lines.Length;i++){if(lines[i].Trim().Length==0)continue;string[] a=lines[i].Trim().Split(' ');if(a.Length!=3||a[0]!="MOVE")throw new Exception("Invalid move line");int x=int.Parse(a[1]),y=int.Parse(a[2]);if(x<0||x>14||y<0||y>14||q.Count>=225||used[x,y])throw new Exception("Invalid replay coordinates");used[x,y]=true;q.Enqueue(new Point(x,y));}new GomokuReview(q,"Validation");return q;
 }
 public static Point Cell(int x,int y){int cx=(int)Math.Round((x-48)/36.0),cy=(int)Math.Round((y-48)/36.0);return cx<0||cx>14||cy<0||cy>14?new Point(-1,-1):new Point(cx,cy);}
 public static void Test(){
  GomokuModel m=new GomokuModel();m.Feed("OK NEW");m.Feed("MOVE 1 7 7 INPUT");m.Feed("BOARD 2 0 1");
  for(int y=0;y<15;y++){char[] r=new string('0',15).ToCharArray();if(y==7)r[7]='1';m.Feed(new string(r));}
  if(!m.Feed("END_BOARD")||m.Board[7,7]!=1||m.Side!=2||m.Count!=1||m.Moves.Count!=1||Cell(300,300)!=new Point(7,7))throw new Exception("Client model test failed");
  bool rejected=false;try{m.Feed("BOARD 1 0 0");m.Feed("bad");}catch{rejected=true;}if(!rejected)throw new Exception("Client accepted corrupt board");
 }
}
public sealed class GomokuReview {
 public readonly List<Point> Moves;public readonly string Source;
 public byte[,] Board {get;private set;}public int Cursor {get;private set;}public int Winner {get;private set;}
 public int Side {get{return Cursor%2+1;}}
 public GomokuReview(IEnumerable<Point> moves,string source){Moves=new List<Point>(moves);Source=source;if(Moves.Count>225)throw new Exception("Replay is longer than225 moves");Jump(Moves.Count);}
 public void Jump(int step){
  if(step<0||step>Moves.Count)throw new Exception("Replay step out of range");
  byte[,] next=new byte[15,15];int winner=0;
  for(int i=0;i<step;i++){
   Point p=Moves[i];if(p.X<0||p.X>=15||p.Y<0||p.Y>=15||next[p.X,p.Y]!=0)throw new Exception("Invalid or repeated replay move");
   if(winner!=0)throw new Exception("Replay contains moves after the game ended");
   byte stone=(byte)(i%2+1);next[p.X,p.Y]=stone;
   int[] dx={1,0,1,1},dy={0,1,1,-1};
   for(int d=0;d<4;d++){
    int length=1;for(int sign=-1;sign<=1;sign+=2){int x=p.X+sign*dx[d],y=p.Y+sign*dy[d];while(x>=0&&x<15&&y>=0&&y<15&&next[x,y]==stone){length++;x+=sign*dx[d];y+=sign*dy[d];}}
    if(length>=5)winner=stone;
   }
  }
  Board=next;Winner=winner;Cursor=step;
 }
 public static void Test(){
  List<Point> game=new List<Point>(new Point[]{new Point(2,7),new Point(1,7),new Point(3,7),new Point(0,0),new Point(4,7),new Point(2,0),new Point(5,7),new Point(4,0),new Point(6,7)});
  GomokuReview r=new GomokuReview(game,"Test");game.Clear();if(r.Moves.Count!=9||r.Winner!=1||r.Side!=2)throw new Exception("Review snapshot/win failed");
  for(int pass=0;pass<3;pass++)for(int step=9;step>=0;step--){r.Jump(step);int occupied=0;for(int y=0;y<15;y++)for(int x=0;x<15;x++)if(r.Board[x,y]!=0)occupied++;if(occupied!=step||r.Cursor!=step||r.Winner!=(step==9?1:0))throw new Exception("Review stepping failed");}
  int who,budget;Queue<Point> q=GomokuModel.ParseReplay(GomokuModel.EncodeReplay(r.Moves,2,"500").Replace("\r","").Split('\n'),out who,out budget);if(q.Count!=9||who!=2||budget!=500)throw new Exception("Review export lost future moves");
  bool rejected=false;try{q.Enqueue(new Point(14,14));new GomokuReview(q,"bad");}catch{rejected=true;}if(!rejected)throw new Exception("Review accepted post-win move");
  rejected=false;try{new GomokuReview(new Point[]{new Point(0,0),new Point(0,0)},"bad");}catch{rejected=true;}if(!rejected)throw new Exception("Review accepted duplicate move");
  GomokuReview empty=new GomokuReview(new Point[0],"Empty");if(empty.Cursor!=0||empty.Winner!=0||empty.Side!=1)throw new Exception("Empty review failed");
 }
}
public sealed class GomokuLink:IDisposable {
 readonly ConcurrentQueue<string> lines=new ConcurrentQueue<string>();
 SerialPort serial;Process child;string tail="";public int CommandsSent {get;private set;}
 public GomokuLink(string port,string exe,bool local){
  if(local){
   ProcessStartInfo start=new ProcessStartInfo(exe);start.UseShellExecute=false;start.CreateNoWindow=true;start.RedirectStandardInput=true;start.RedirectStandardOutput=true;start.RedirectStandardError=true;
   child=new Process();child.StartInfo=start;child.OutputDataReceived+=(s,e)=>{if(e.Data!=null)lines.Enqueue(e.Data);};child.ErrorDataReceived+=(s,e)=>{if(e.Data!=null)lines.Enqueue("ERROR HOST "+e.Data);};
   child.Start();child.BeginOutputReadLine();child.BeginErrorReadLine();
  }else{serial=new SerialPort(port,115200,Parity.None,8,StopBits.One);serial.Handshake=Handshake.None;serial.DtrEnable=false;serial.RtsEnable=false;serial.WriteTimeout=500;serial.Open();}
 }
 public void Send(string s){if(child!=null){child.StandardInput.WriteLine(s);child.StandardInput.Flush();}else serial.Write(s+"\n");CommandsSent++;}
 public bool Read(out string s){
  if(serial!=null){tail+=serial.ReadExisting();int p;while((p=tail.IndexOf('\n'))>=0){lines.Enqueue(tail.Substring(0,p).Trim('\r'));tail=tail.Substring(p+1);}if(tail.Length>4096)throw new Exception("Oversized serial response");}
  return lines.TryDequeue(out s);
 }
 public void Dispose(){if(serial!=null){serial.Close();serial.Dispose();}if(child!=null){try{child.StandardInput.Close();if(!child.WaitForExit(200))child.Kill();}finally{child.Dispose();}}}
}
public sealed class GomokuBoard:Panel {
 public GomokuBoard(){SetStyle(ControlStyles.UserPaint|ControlStyles.AllPaintingInWmPaint|ControlStyles.OptimizedDoubleBuffer|ControlStyles.ResizeRedraw,true);}
 public void ClickCell(int x,int y){OnMouseClick(new MouseEventArgs(MouseButtons.Left,1,48+x*36,48+y*36,0));}
 public void MovePointer(int x,int y){OnMouseMove(new MouseEventArgs(MouseButtons.None,0,x,y,0));}
}
public sealed class GomokuWindow:Form {
 readonly GomokuModel model=new GomokuModel();
 readonly GomokuBoard board=new GomokuBoard();readonly TextBox log=new TextBox();readonly Label state=new Label(),stats=new Label();
 readonly ComboBox thinking=new ComboBox(),colour=new ComboBox();
 readonly Button fresh=new Button(),undo=new Button(),stop=new Button(),resume=new Button(),save=new Button(),load=new Button();
 readonly Button review=new Button(),reviewFirst=new Button(),reviewPrev=new Button(),reviewNext=new Button(),reviewLast=new Button(),reviewExit=new Button();
 readonly NumericUpDown reviewStep=new NumericUpDown();readonly Label reviewPosition=new Label();readonly ListBox reviewMoves=new ListBox();
 GomokuReview reviewing;int reviewHuman,reviewBudget;bool updatingReview;string liveStats="";
 readonly Timer timer=new Timer();GomokuLink link;bool busy=true,started,suspended,loading,preview;int human=1;long hz=80000000;
 Queue<Point> replay=new Queue<Point>();Point hover=new Point(-1,-1);readonly Stopwatch silence=new Stopwatch();
 public GomokuWindow(string port,string exe,bool local,bool offline){
  preview=offline;Text=offline?"Gomoku - OFFLINE UI PREVIEW":local?"Gomoku - HOST TEST (AI runs on this PC)":"Gomoku - FPGA "+port+" / 115200 8N1";
  ClientSize=new Size(1030,760);FormBorderStyle=FormBorderStyle.FixedSingle;MaximizeBox=false;Font=new Font("Segoe UI",10);
  state.SetBounds(12,12,1000,28);state.Text="Connecting...  15x15 freestyle: five or more wins. No forbidden moves.";Controls.Add(state);
  string[] names={"New","Undo","Stop","Think","Save","Load"};Button[] buttons={fresh,undo,stop,resume,save,load};
  for(int i=0;i<buttons.Length;i++){buttons[i].Text=names[i];buttons[i].SetBounds(12+i*86,45,80,28);Controls.Add(buttons[i]);}
  colour.DropDownStyle=ComboBoxStyle.DropDownList;colour.Items.AddRange(new object[]{"Black (New game)","White (New game)"});colour.SelectedIndex=0;colour.SetBounds(545,45,145,28);Controls.Add(colour);
  thinking.DropDownStyle=ComboBoxStyle.DropDownList;thinking.Items.AddRange(new object[]{"100","500","1000","3000","5000"});thinking.SelectedItem="1000";thinking.SetBounds(700,45,100,28);Controls.Add(thinking);
  Label units=new Label();units.Text="ms / move";units.SetBounds(808,49,110,24);Controls.Add(units);
  review.Text="Review";review.SetBounds(926,45,86,28);Controls.Add(review);
  Button[] navigation={reviewFirst,reviewPrev,reviewNext,reviewLast,reviewExit};string[] navigationText={"First","Prev","Next","Last","Exit review"};
  for(int i=0;i<navigation.Length;i++){navigation[i].Text=navigationText[i];navigation[i].SetBounds(12+i*78,85,i==4?110:70,28);Controls.Add(navigation[i]);}
  Label stepLabel=new Label();stepLabel.Text="Step:";stepLabel.SetBounds(450,89,45,24);Controls.Add(stepLabel);
  reviewStep.SetBounds(500,85,70,28);reviewStep.Minimum=0;Controls.Add(reviewStep);
  reviewPosition.SetBounds(582,89,430,24);reviewPosition.Text="Review current game or open a saved .gmk.";Controls.Add(reviewPosition);
  review.Click+=(s,e)=>BeginReview(model.Moves,human,int.Parse(thinking.Text),"Current game",model.Moves.Count);
  reviewFirst.Click+=(s,e)=>JumpReview(0);reviewPrev.Click+=(s,e)=>JumpReview(reviewing.Cursor-1);reviewNext.Click+=(s,e)=>JumpReview(reviewing.Cursor+1);reviewLast.Click+=(s,e)=>JumpReview(reviewing.Moves.Count);reviewExit.Click+=(s,e)=>EndReview();
  reviewStep.ValueChanged+=(s,e)=>{if(reviewing!=null&&!updatingReview)JumpReview((int)reviewStep.Value);};
  KeyPreview=true;KeyDown+=(s,e)=>{if(reviewing!=null){if(e.KeyCode==Keys.Left)JumpReview(reviewing.Cursor-1);else if(e.KeyCode==Keys.Right)JumpReview(reviewing.Cursor+1);else if(e.KeyCode==Keys.Home)JumpReview(0);else if(e.KeyCode==Keys.End)JumpReview(reviewing.Moves.Count);else return;e.Handled=true;e.SuppressKeyPress=true;}};
  board.SetBounds(12,130,600,600);board.BackColor=Color.FromArgb(226,185,120);board.Paint+=PaintBoard;board.MouseMove+=(s,e)=>SetHover(GomokuModel.Cell(e.X,e.Y));board.MouseLeave+=(s,e)=>SetHover(new Point(-1,-1));
  board.MouseClick+=(s,e)=>{Point p=GomokuModel.Cell(e.X,e.Y);if(reviewing==null&&!busy&&!suspended&&model.Side==human&&model.Winner==0&&model.Count<225&&p.X>=0&&model.Board[p.X,p.Y]==0)SendBusy("PLAY "+p.X+" "+p.Y);};Controls.Add(board);
  stats.SetBounds(632,135,380,185);stats.Font=new Font("Consolas",10);stats.Text="Search is performed by the selected engine.\nNo completed search yet.";Controls.Add(stats);
  log.SetBounds(632,325,380,405);log.Multiline=true;log.ReadOnly=true;log.ScrollBars=ScrollBars.Vertical;log.Font=new Font("Consolas",9);Controls.Add(log);
  reviewMoves.SetBounds(632,325,380,405);reviewMoves.Font=new Font("Consolas",10);reviewMoves.Visible=false;Controls.Add(reviewMoves);
  reviewMoves.SelectedIndexChanged+=(s,e)=>{if(reviewing!=null&&!updatingReview&&reviewMoves.SelectedIndex>=0)JumpReview(reviewMoves.SelectedIndex);};
  fresh.Click+=(s,e)=>NewGame();undo.Click+=(s,e)=>{suspended=false;SendBusy("UNDO "+(model.Side==human?2:1));};stop.Click+=(s,e)=>{suspended=true;link.Send("STOP");};resume.Click+=(s,e)=>{suspended=false;Think();};save.Click+=SaveGame;load.Click+=LoadGame;
  thinking.SelectedIndexChanged+=(s,e)=>{if(link!=null&&!busy&&reviewing==null)link.Send("TIME "+thinking.Text);};
  timer.Interval=15;timer.Tick+=(s,e)=>Poll();FormClosed+=(s,e)=>{timer.Stop();if(link!=null)link.Dispose();timer.Dispose();};
  if(!offline){link=new GomokuLink(port,exe,local);link.Send("PING");silence.Start();timer.Start();}UpdateControls();
 }
 void SendBusy(string s){if(reviewing!=null)throw new Exception("Exit review before sending game commands");busy=true;silence.Restart();link.Send(s);UpdateControls();}
 void SetHover(Point next){
  if(next==hover)return;
  Point previous=hover;hover=next;
  if(previous.X>=0)board.Invalidate(new Rectangle(30+previous.X*36,30+previous.Y*36,36,36));
  if(next.X>=0)board.Invalidate(new Rectangle(30+next.X*36,30+next.Y*36,36,36));
 }
 void NewGame(){if(reviewing!=null)return;loading=false;replay.Clear();human=colour.SelectedIndex+1;suspended=false;link.Send("TIME "+thinking.Text);SendBusy("NEW");}
 void Think(){if(reviewing!=null)return;if(model.Winner==0&&model.Count<225){state.Text="Engine thinking...";SendBusy("GO");}}
 void UpdateControls(){
  bool idle=!busy&&reviewing==null&&link!=null;
  fresh.Enabled=colour.Enabled=thinking.Enabled=idle;load.Enabled=!busy;
  undo.Enabled=idle&&model.Count>=2;stop.Enabled=busy&&started&&reviewing==null&&link!=null;
  resume.Enabled=idle&&suspended&&model.Side!=human&&model.Winner==0;
  save.Enabled=!busy&&(reviewing!=null||model.Moves.Count==model.Count);review.Enabled=idle&&!loading&&started;
  bool active=reviewing!=null;reviewFirst.Enabled=reviewPrev.Enabled=active&&reviewing.Cursor>0;
  reviewNext.Enabled=reviewLast.Enabled=active&&reviewing.Cursor<reviewing.Moves.Count;reviewExit.Enabled=active&&link!=null;reviewStep.Enabled=active;
  load.Text=active?"Open .gmk":"Load";log.Visible=!active;reviewMoves.Visible=active;
 }
 void BeginReview(IEnumerable<Point> moves,int who,int budget,string source,int step){
  GomokuReview next=new GomokuReview(moves,source);next.Jump(step);
  if(reviewing==null)liveStats=stats.Text;reviewing=next;reviewHuman=who;reviewBudget=budget;
  updatingReview=true;reviewMoves.Items.Clear();reviewMoves.Items.Add("000  Start (empty board)");for(int i=0;i<next.Moves.Count;i++){Point p=next.Moves[i];reviewMoves.Items.Add(String.Format("{0:000}  {1,-5}  {2}{3}",i+1,i%2==0?"Black":"White",(char)('A'+p.X),p.Y+1));}updatingReview=false;
  SetHover(new Point(-1,-1));RefreshReview();
 }
 void JumpReview(int step){if(reviewing==null)return;reviewing.Jump(Math.Max(0,Math.Min(reviewing.Moves.Count,step)));RefreshReview();}
 void RefreshReview(){
  updatingReview=true;reviewStep.Maximum=reviewing.Moves.Count;reviewStep.Value=reviewing.Cursor;reviewMoves.SelectedIndex=reviewing.Cursor;updatingReview=false;
  string last="None";if(reviewing.Cursor>0){Point p=reviewing.Moves[reviewing.Cursor-1];last=((char)('A'+p.X)).ToString()+(p.Y+1)+" ("+(reviewing.Cursor%2==1?"Black":"White")+")";}
  reviewPosition.Text="/ "+reviewing.Moves.Count+"   Last: "+last;
  state.Text="REVIEW - "+reviewing.Source+"  |  Step "+reviewing.Cursor+" / "+reviewing.Moves.Count+"  |  "+(reviewing.Winner!=0?(reviewing.Winner==1?"Black":"White")+" wins":reviewing.Cursor==225?"Draw":(reviewing.Side==1?"Black":"White")+" to move");
  stats.Text="Review only - no AI search.\n\nLeft / Right: previous / next\nHome / End: first / last\nStep box or move list: jump\nOpen .gmk: browse another record\nSave: export the complete record\n\n"+(link!=null?"Live game and search statistics\nare preserved until Exit review.":"Offline replay.\nNo FPGA connection required.");
  board.Invalidate();UpdateControls();
 }
 void EndReview(){if(reviewing==null||link==null)return;reviewing=null;stats.Text=liveStats;reviewPosition.Text="Review current game or open a saved .gmk.";UpdateState();board.Invalidate();UpdateControls();}
 void UpdateState(){state.Text=model.Winner!=0?(model.Winner==1?"Black":"White")+" wins":model.Count==225?"Draw":(model.Side==human?"Your turn":"Engine turn")+(suspended?" - paused":"")+"  |  Moves: "+model.Count;}
 void OpenReplay(string path){
  int who,budget;Queue<Point> moves=GomokuModel.ParseReplay(File.ReadAllLines(path),out who,out budget);
  BeginReview(moves,who,budget,Path.GetFileName(path),0);
 }
 void Poll(){try{string line;int n=0;while(n++<512&&link.Read(out line))Receive(line);if(busy&&silence.ElapsedMilliseconds>15000){state.Text="No complete response. Check COM port, FPGA image, or press board reset.";}}catch(Exception e){timer.Stop();MessageBox.Show(e.Message,"Connection error");busy=false;UpdateControls();}}
 void Receive(string line){
  line=line.Trim();if(line.Length==0)return;
  if(line.Length!=15 || line[0]<'0'||line[0]>'2'){log.AppendText(line+Environment.NewLine);if(log.TextLength>60000)log.Text=log.Text.Substring(log.TextLength-40000);}
  if(line.StartsWith("HELLO ")){
   Match h=Regex.Match(line,@"hz=(\d+)");if(h.Success)hz=long.Parse(h.Groups[1].Value);
   if(!started){started=true;if(!preview)NewGame();}return;
  }
  if(line.StartsWith("ERROR ")){loading=false;replay.Clear();busy=false;suspended=true;state.Text=line;UpdateControls();return;}
  if(line=="CANCELLED")suspended=true;
  if(line.StartsWith("INFO ")){
   Dictionary<string,double> v=new Dictionary<string,double>();foreach(Match m in Regex.Matches(line,@"(\w+)=(-?\d+)"))v[m.Groups[1].Value]=double.Parse(m.Groups[2].Value,System.Globalization.CultureInfo.InvariantCulture);
   double cycles=v["cycles"],nodes=v["nodes"],ms=cycles/hz*1000,nps=cycles>0?nodes*hz/cycles:0;
   stats.Text=String.Format(System.Globalization.CultureInfo.InvariantCulture,"Depth: {0}   Score: {1}\nNodes: {2:N0}   NPS: {3:N0}\nCompute: {4:F2} ms\nCycles: {5:N0}\nInstructions: {6:N0}\nIPC: {7}\nTT hits: {8}   Cutoffs: {9}\nStopped/budget: {10}\n{11}",v["depth"],v["score"],nodes,nps,ms,cycles,v["instret"],v["instret"]>0&&cycles>0?(v["instret"]/cycles).ToString("F3",System.Globalization.CultureInfo.InvariantCulture):"HOST: not measured",v["tt_hits"],v["cutoffs"],v["stopped"],preview?"Preview from captured HOST test":"CPU ROI excludes reply transmission");
  }
  if(model.Feed(line)){
   busy=false;if(reviewing!=null){suspended=true;RefreshReview();return;}if(model.Side==human)suspended=false;board.Invalidate();
   UpdateState();
   if(!preview){
    if(loading&&replay.Count>0){Point p=replay.Dequeue();SendBusy("PLAY "+p.X+" "+p.Y);}
    else {loading=false;if(!suspended&&model.Winner==0&&model.Count<225&&model.Side!=human)Think();}
   }
   UpdateControls();
  }
 }
 void PaintBoard(object sender,PaintEventArgs e){
  byte[,] view=reviewing!=null?reviewing.Board:model.Board;List<Point> moves=reviewing!=null?reviewing.Moves:model.Moves;int count=reviewing!=null?reviewing.Cursor:moves.Count;
  Graphics g=e.Graphics;g.SmoothingMode=System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
  using(Pen grid=new Pen(Color.FromArgb(65,45,20)))for(int i=0;i<15;i++){g.DrawLine(grid,48,48+i*36,552,48+i*36);g.DrawLine(grid,48+i*36,48,48+i*36,552);}
  using(Font f=new Font("Segoe UI",9))for(int i=0;i<15;i++){g.DrawString((i+1).ToString(),f,Brushes.Black,22,40+i*36);g.DrawString(((char)('A'+i)).ToString(),f,Brushes.Black,42+i*36,20);}
  foreach(int y in new int[]{3,7,11})foreach(int x in new int[]{3,7,11})g.FillEllipse(Brushes.Black,45+x*36,45+y*36,6,6);
  for(int y=0;y<15;y++)for(int x=0;x<15;x++)if(view[x,y]!=0){int px=48+x*36,py=48+y*36;g.FillEllipse(view[x,y]==1?Brushes.Black:Brushes.White,px-15,py-15,30,30);g.DrawEllipse(Pens.DimGray,px-15,py-15,30,30);}
  if(reviewing!=null)using(Font numberFont=new Font("Segoe UI",9,FontStyle.Bold))using(StringFormat format=new StringFormat()){format.Alignment=StringAlignment.Center;format.LineAlignment=StringAlignment.Center;for(int i=0;i<count;i++){Point stone=moves[i];g.DrawString((i+1).ToString(),numberFont,i%2==0?Brushes.White:Brushes.Black,new RectangleF(33+stone.X*36,33+stone.Y*36,30,30),format);}}
  if(count>0){Point p=moves[count-1];g.DrawRectangle(Pens.Red,31+p.X*36,31+p.Y*36,34,34);}
  if(reviewing==null&&!busy&&!suspended&&model.Side==human&&model.Winner==0&&hover.X>=0&&model.Board[hover.X,hover.Y]==0)g.DrawEllipse(Pens.RoyalBlue,34+hover.X*36,34+hover.Y*36,28,28);
 }
 void SaveGame(object sender,EventArgs e){using(SaveFileDialog d=new SaveFileDialog()){d.Filter="Gomoku replay|*.gmk";if(d.ShowDialog()!=DialogResult.OK)return;File.WriteAllText(d.FileName,reviewing!=null?GomokuModel.EncodeReplay(reviewing.Moves,reviewHuman,reviewBudget.ToString()):model.Replay(human,thinking.Text),Encoding.UTF8);}}
 void LoadGame(object sender,EventArgs e){using(OpenFileDialog d=new OpenFileDialog()){d.Filter="Gomoku replay|*.gmk";if(d.ShowDialog()!=DialogResult.OK)return;try{
  if(reviewing!=null){OpenReplay(d.FileName);return;}
  int who,budget;Queue<Point> q=GomokuModel.ParseReplay(File.ReadAllLines(d.FileName),out who,out budget);
  human=who;colour.SelectedIndex=who-1;if(!thinking.Items.Contains(budget.ToString()))thinking.Items.Add(budget.ToString());thinking.SelectedItem=budget.ToString();loading=true;replay=q;suspended=false;link.Send("TIME "+budget);SendBusy("NEW");
 }catch(Exception ex){MessageBox.Show(ex.Message,"Replay error");}}}
 void ShowOffscreen(){StartPosition=FormStartPosition.Manual;Location=new Point(-20000,-20000);ShowInTaskbar=false;Show();Application.DoEvents();}
 void WaitFor(Func<bool> predicate){Stopwatch watch=Stopwatch.StartNew();while(!predicate()){Application.DoEvents();System.Threading.Thread.Sleep(5);if(watch.ElapsedMilliseconds>10000)throw new Exception("GUI/host test timeout: "+state.Text);}}
 public static void TestHost(string exe,string screenshot){
  Application.EnableVisualStyles();using(GomokuWindow w=new GomokuWindow(null,exe,true,false)){
   w.ShowOffscreen();w.WaitFor(()=>w.started&&!w.busy&&w.model.Count==0);w.thinking.SelectedItem="100";
   int invalidations=0;w.board.Invalidated+=(s,e)=>invalidations++;
   w.board.MovePointer(300,300);int firstHover=invalidations;
   for(int i=1;i<=8;i++)w.board.MovePointer(300+i,300+i);
   if(invalidations!=firstHover)throw new Exception("Mouse movement inside one cell repainted the board");
   w.board.MovePointer(336,300);if(invalidations<=firstHover)throw new Exception("Hover did not update after crossing cells");
   w.board.ClickCell(7,7);w.WaitFor(()=>!w.busy&&w.model.Count==2);if(w.model.Board[7,7]!=1)throw new Exception("GUI human move not applied");
   w.undo.PerformClick();w.WaitFor(()=>!w.busy&&w.model.Count==0);
   w.colour.SelectedIndex=1;w.fresh.PerformClick();w.WaitFor(()=>!w.busy&&w.model.Count==1&&w.model.Side==2);
   w.thinking.SelectedItem="5000";w.board.ClickCell(6,6);w.WaitFor(()=>w.busy&&w.model.Count==2);w.stop.PerformClick();
   w.WaitFor(()=>!w.busy&&w.suspended);if(w.model.Count!=2)throw new Exception("GUI cancellation committed AI move");
   int who,budget;Queue<Point> q=GomokuModel.ParseReplay(w.model.Replay(2,"100").Replace("\r","").Split('\n'),out who,out budget);
   if(q.Count!=2||who!=2||budget!=100)throw new Exception("Replay roundtrip failed");
   w.human=who;w.loading=true;w.replay=q;w.suspended=false;w.link.Send("TIME 100");w.SendBusy("NEW");w.WaitFor(()=>!w.busy&&w.model.Count==3);
   if(w.model.Moves[0]!=new Point(7,7)||w.model.Moves[1]!=new Point(6,6))throw new Exception("GUI replay differs");
   // Actual form controls browse a detached snapshot and must send zero engine commands.
   int sent=w.link.CommandsSent,liveCount=w.model.Count;string live=w.model.Replay(w.human,w.thinking.Text),statsBefore=w.stats.Text;
   w.review.PerformClick();if(w.reviewing==null||w.reviewing.Cursor!=liveCount)throw new Exception("Review entry failed");
   w.reviewFirst.PerformClick();if(w.reviewing.Cursor!=0||w.reviewing.Board[7,7]!=0)throw new Exception("Review first failed");
   w.reviewNext.PerformClick();if(w.reviewing.Cursor!=1||w.reviewing.Board[7,7]!=1)throw new Exception("Review next failed");
   w.reviewLast.PerformClick();w.reviewPrev.PerformClick();if(w.reviewing.Cursor!=liveCount-1)throw new Exception("Review previous failed");
   w.reviewStep.Value=1;if(w.reviewing.Cursor!=1)throw new Exception("Review step box failed");w.reviewMoves.SelectedIndex=2;if(w.reviewing.Cursor!=2)throw new Exception("Review move-list selection failed");
   w.OnKeyDown(new KeyEventArgs(Keys.Home));if(w.reviewing.Cursor!=0)throw new Exception("Review Home key failed");w.OnKeyDown(new KeyEventArgs(Keys.Right));if(w.reviewing.Cursor!=1)throw new Exception("Review Right key failed");w.OnKeyDown(new KeyEventArgs(Keys.End));if(w.reviewing.Cursor!=liveCount)throw new Exception("Review End key failed");w.OnKeyDown(new KeyEventArgs(Keys.Left));if(w.reviewing.Cursor!=liveCount-1)throw new Exception("Review Left key failed");
   w.board.ClickCell(0,0);if(w.link.CommandsSent!=sent||w.model.Replay(w.human,w.thinking.Text)!=live)throw new Exception("Review changed live game");
   if(w.fresh.Enabled||w.undo.Enabled||w.resume.Enabled||w.thinking.Enabled)throw new Exception("Live controls enabled while reviewing");
   string file=Path.GetTempFileName();try{
    File.WriteAllText(file,"GOMOKU1 15 FREESTYLE\nHUMAN 1\nTIME 1000\nMOVE 2 7\nMOVE 1 7\nMOVE 3 7\nMOVE 0 0\nMOVE 4 7\nMOVE 2 0\nMOVE 5 7\nMOVE 4 0\nMOVE 6 7\n");
    w.OpenReplay(file);if(w.reviewing.Cursor!=0||w.reviewing.Moves.Count!=9)throw new Exception("Open replay failed");
    w.reviewLast.PerformClick();if(w.reviewing.Winner!=1||w.reviewing.Cursor!=9)throw new Exception("Review winner failed");
    if(w.link.CommandsSent!=sent||w.model.Replay(w.human,w.thinking.Text)!=live)throw new Exception("File review touched live engine");
    GomokuReview valid=w.reviewing;File.WriteAllText(file,"GOMOKU1 15 FREESTYLE\nHUMAN 1\nTIME 1000\nMOVE 0 0\nMOVE 0 0\n");bool rejected=false;try{w.OpenReplay(file);}catch{rejected=true;}if(!rejected||w.reviewing!=valid)throw new Exception("Invalid replay replaced valid review");
    if(!String.IsNullOrEmpty(screenshot))using(Bitmap image=new Bitmap(w.Width,w.Height)){w.DrawToBitmap(image,new Rectangle(0,0,w.Width,w.Height));image.Save(screenshot,System.Drawing.Imaging.ImageFormat.Png);}
   }finally{File.Delete(file);}
   w.reviewExit.PerformClick();if(w.reviewing!=null||w.stats.Text!=statsBefore||w.link.CommandsSent!=sent||w.model.Count!=liveCount)throw new Exception("Review exit did not restore live view");
   w.thinking.SelectedItem="100";w.board.ClickCell(0,0);w.WaitFor(()=>!w.busy&&w.model.Count==liveCount+2);if(w.model.Board[0,0]!=w.human)throw new Exception("Cannot continue game after review");
   w.Hide();
  }
  // No host executable or serial device is opened for offline browsing.
  using(GomokuWindow w=new GomokuWindow(null,null,false,true)){
   w.busy=false;w.BeginReview(new Point[]{new Point(7,7),new Point(6,7)},1,1000,"Offline test",0);w.ShowOffscreen();w.reviewNext.PerformClick();
   if(w.link!=null||w.reviewing.Cursor!=1||w.fresh.Enabled||w.reviewExit.Enabled||w.thinking.Enabled||!w.load.Enabled)throw new Exception("Offline replay controls failed");w.Hide();
  }
 }
 public void MakePreview(string path,string trace){
  foreach(string line in File.ReadAllLines(trace))Receive(line);ShowOffscreen();
  using(Bitmap image=new Bitmap(Width,Height)){DrawToBitmap(image,new Rectangle(0,0,Width,Height));image.Save(path,System.Drawing.Imaging.ImageFormat.Png);}
 }
 public static void StartReview(string file){Application.EnableVisualStyles();using(GomokuWindow w=new GomokuWindow(null,null,false,true)){w.busy=false;w.Text="Gomoku - OFFLINE REPLAY";w.OpenReplay(file);Application.Run(w);}}
 public static void Start(string port,string exe,bool local){Application.EnableVisualStyles();Application.Run(new GomokuWindow(port,exe,local,false));}
 public static void Preview(string path,string trace){Application.EnableVisualStyles();using(GomokuWindow w=new GomokuWindow(null,null,false,true))w.MakePreview(path,trace);}
}
'@
Add-Type -TypeDefinition $code -ReferencedAssemblies System.Windows.Forms,System.Drawing
if ($SelfTest) { [GomokuModel]::Test(); [GomokuReview]::Test(); 'PASS: desktop parser and detached replay stepping/winner/validation/export'; exit 0 }
if ($UiTest) { [GomokuWindow]::TestHost($hostExe,$Preview); 'PASS: actual desktop/host game, cancellation, load, review navigation/file/winner, live state preserved and zero engine commands while reviewing'; exit 0 }
if ($Review) { [GomokuWindow]::StartReview((Resolve-Path -LiteralPath $Review).Path); exit 0 }
if ($Preview) { if(-not $ReplayLog){throw '-Preview requires -ReplayLog from a captured host test'}; [GomokuWindow]::Preview($Preview,$ReplayLog); exit 0 }
[GomokuWindow]::Start($Port,$hostExe,[bool]$Local)
