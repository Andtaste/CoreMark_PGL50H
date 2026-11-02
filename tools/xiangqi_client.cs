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

public sealed class XiangqiModel {
 public byte[] Board=StartBoard();public int Side,Outcome,Count,Checked;
 public readonly List<Point> Moves=new List<Point>();
 public byte[] InitialBoard=StartBoard();public int InitialSide;public string InitialFen;
 string pendingFen;
 public static string ParseFen(string text,out byte[] board,out int side){
  string[] a=Regex.Split(text.Trim(),@"\s+");
  if(a.Length!=2&&a.Length!=6)throw new Exception("FEN需要棋盘和行棋方，可附标准计数字段");
  if(a.Length==6&&(!Regex.IsMatch(a[2]+" "+a[3]+" "+a[4]+" "+a[5],@"^- - [0-9]+ [0-9]+$")))throw new Exception("Invalid FEN suffix");
  if(a[1]!="w"&&a[1]!="r"&&a[1]!="b")throw new Exception("Invalid FEN side");
  side=a[1]=="b"?1:0;board=new byte[90];string[] ranks=a[0].Split('/');if(ranks.Length!=10)throw new Exception("FEN必须有10行");
  int[,] counts=new int[2,7];
  for(int y=0;y<10;y++){int x=0;foreach(char c in ranks[y]){if(c>='1'&&c<='9'){x+=c-'0';if(x>9)throw new Exception("Invalid FEN rank");continue;}
   char lower=char.ToLowerInvariant(c);if(lower=='h')lower='n';if(lower=='e')lower='b';int type="kabnrcp".IndexOf(lower),owner=char.IsLower(c)?1:0;
   if(type<0||x>=9||++counts[owner,type]>(type==0?1:type==6?5:2))throw new Exception("Invalid FEN pieces");
   if(type==0&&(x<3||x>5||(owner==1?y>2:y<7)))throw new Exception("将帅必须在九宫内");board[y*9+x++]=(byte)(type+1+owner*7);
  }if(x!=9)throw new Exception("FEN每行必须有9格");}
  if(counts[0,0]!=1||counts[1,0]!=1)throw new Exception("FEN必须包含双方将帅");
  return a[0]+" "+(side==0?"w":"b");
 }
 public string PrepareFen(string text){byte[] b;int side;pendingFen=ParseFen(text,out b,out side);return pendingFen;}
 public void CancelFen(){pendingFen=null;}
 void SetInitial(string fen){if(fen==null){InitialFen=null;InitialBoard=StartBoard();InitialSide=0;}else InitialFen=ParseFen(fen,out InitialBoard,out InitialSide);Moves.Clear();}

 byte[] incoming;int rows,inSide,inOutcome,inCount,inCheck;
 public static byte[] StartBoard(){
  string[] lines={"CBA989ABC","000000000","0D00000D0","E0E0E0E0E","000000000","000000000","707070707","060000060","000000000","543212345"};
  byte[] b=new byte[90];for(int y=0;y<10;y++)for(int x=0;x<9;x++)b[y*9+x]=Convert.ToByte(lines[y].Substring(x,1),16);return b;
 }
 public static int Cell(int x,int y){int cx=(int)Math.Round((x-48)/56.0),cy=(int)Math.Round((y-48)/56.0);return cx<0||cx>=9||cy<0||cy>=10?-1:cy*9+cx;}
 static bool Own(byte piece,int side){return piece>0 && (piece<=7?0:1)==side;}
 public bool Feed(string line){
  line=line.Trim();if(line.Length==0)return false;string[] a=line.Split(new char[]{' '},StringSplitOptions.RemoveEmptyEntries);
  if(incoming!=null && rows<10){
   if(line.Length!=9)throw new Exception("Incomplete board row");
   for(int x=0;x<9;x++){if(!Uri.IsHexDigit(line[x]))throw new Exception("Invalid board byte");byte v=Convert.ToByte(line.Substring(x,1),16);if(v>14)throw new Exception("Unknown piece");incoming[rows*9+x]=v;}rows++;return false;
  }
  if(a[0]=="BOARD" && a.Length==5){inSide=int.Parse(a[1]);inOutcome=int.Parse(a[2]);inCount=int.Parse(a[3]);inCheck=int.Parse(a[4]);incoming=new byte[90];rows=0;return false;}
  if(a[0]=="END_BOARD"){
   if(incoming==null||rows!=10||inCount!=Moves.Count||inSide!=(InitialSide+inCount)%2||inOutcome<0||inOutcome>3||inCheck<0||inCheck>1)throw new Exception("Board/history/turn mismatch");
   byte[] expected=(byte[])InitialBoard.Clone();
   for(int i=0;i<Moves.Count;i++){Point p=Moves[i];if(!Own(expected[p.X],(InitialSide+i)%2)||Own(expected[p.Y],(InitialSide+i)%2))throw new Exception("Invalid move history");expected[p.Y]=expected[p.X];expected[p.X]=0;}
   for(int i=0;i<90;i++)if(incoming[i]!=expected[i])throw new Exception("Board differs from move history");
   Board=incoming;incoming=null;Side=inSide;Outcome=inOutcome;Count=inCount;Checked=inCheck;return true;
  }
  if(line=="OK NEW"){SetInitial(null);pendingFen=null;return false;}
  if(line=="OK FEN"){if(pendingFen==null)throw new Exception("Unexpected FEN acknowledgement");SetInitial(pendingFen);pendingFen=null;return false;}
  if(a[0]=="MOVE" && a.Length==5){int side=int.Parse(a[1]),from=int.Parse(a[2]),to=int.Parse(a[3]);if(side!=(InitialSide+Moves.Count)%2||from<0||from>=90||to<0||to>=90||from==to)throw new Exception("Invalid move");Moves.Add(new Point(from,to));}
  if(a[0]=="OK"&&a.Length==3&&a[1]=="UNDO"){int n=int.Parse(a[2]);if(n<1||n>Moves.Count)throw new Exception("Invalid undo");Moves.RemoveRange(Moves.Count-n,n);}
  return false;
 }
 public string Replay(int human,string budget){StringBuilder s=new StringBuilder("XIANGQI1 "+(InitialFen==null?"START":"FEN "+InitialFen)+"\nHUMAN "+human+"\nTIME "+budget+"\n");foreach(Point p in Moves)s.AppendLine("MOVE "+p.X+" "+p.Y);return s.ToString();}
 public static Queue<Point> ParseReplay(string[] lines,out int human,out int budget){
  string fen;Queue<Point> q=ParseReplay(lines,out human,out budget,out fen);if(fen!=null)throw new Exception("请使用双棋客户端导入残局棋谱");return q;
 }
 public static Queue<Point> ParseReplay(string[] lines,out int human,out int budget,out string fen){
  fen=null;
  if(lines.Length<3||(lines[0]!="XIANGQI1 START"&&!lines[0].StartsWith("XIANGQI1 FEN "))||!lines[1].StartsWith("HUMAN ")||!lines[2].StartsWith("TIME "))throw new Exception("Invalid replay header");
  human=int.Parse(lines[1].Substring(6));budget=int.Parse(lines[2].Substring(5));if(human<0||human>1||budget<50||budget>10000)throw new Exception("Invalid replay settings");
  Queue<Point> q=new Queue<Point>();byte[] b=StartBoard();int side=0;if(lines[0].StartsWith("XIANGQI1 FEN "))fen=ParseFen(lines[0].Substring(13),out b,out side);
  for(int i=3;i<lines.Length;i++){if(lines[i].Trim().Length==0)continue;string[] a=lines[i].Trim().Split(' ');if(a.Length!=3||a[0]!="MOVE")throw new Exception("Invalid replay line");int from=int.Parse(a[1]),to=int.Parse(a[2]);if(from<0||from>=90||to<0||to>=90||from==to||q.Count>=957||!Own(b[from],side)||Own(b[to],side))throw new Exception("Invalid replay move");q.Enqueue(new Point(from,to));b[to]=b[from];b[from]=0;side=1-side;}return q;
 }
 public static void Test(){
  XiangqiModel m=new XiangqiModel();m.Feed("OK NEW");m.Feed("MOVE 0 54 45 INPUT");byte[] b=StartBoard();b[45]=b[54];b[54]=0;m.Feed("BOARD 1 0 1 0");
  for(int y=0;y<10;y++){StringBuilder row=new StringBuilder();for(int x=0;x<9;x++)row.Append(b[y*9+x].ToString("X"));m.Feed(row.ToString());}
  if(!m.Feed("END_BOARD")||m.Board[45]!=7||m.Board[54]!=0||Cell(48,384)!=54)throw new Exception("Board parser failed");
  bool bad=false;try{m.Feed("BOARD 0 0 2 0");m.Feed("bad");}catch{bad=true;}if(!bad)throw new Exception("Corrupt board accepted");
 }
}
public sealed class XiangqiLink:IDisposable {
 readonly ConcurrentQueue<string> lines=new ConcurrentQueue<string>();SerialPort serial;Process child;string tail="";
 public XiangqiLink(string port,string exe,bool local){
  if(local){ProcessStartInfo s=new ProcessStartInfo(exe);s.UseShellExecute=false;s.CreateNoWindow=true;s.RedirectStandardInput=true;s.RedirectStandardOutput=true;s.RedirectStandardError=true;child=new Process();child.StartInfo=s;child.OutputDataReceived+=(o,e)=>{if(e.Data!=null)lines.Enqueue(e.Data);};child.ErrorDataReceived+=(o,e)=>{if(e.Data!=null)lines.Enqueue("ERROR HOST "+e.Data);};child.Start();child.BeginOutputReadLine();child.BeginErrorReadLine();}
  else{serial=new SerialPort(port,115200,Parity.None,8,StopBits.One);serial.Handshake=Handshake.None;serial.DtrEnable=false;serial.RtsEnable=false;serial.WriteTimeout=500;serial.Open();}
 }
 public void Send(string s){if(child!=null){child.StandardInput.WriteLine(s);child.StandardInput.Flush();}else serial.Write(s+"\n");}
 public bool Read(out string line){if(serial!=null){tail+=serial.ReadExisting();int p;while((p=tail.IndexOf('\n'))>=0){lines.Enqueue(tail.Substring(0,p).Trim('\r'));tail=tail.Substring(p+1);}if(tail.Length>4096)throw new Exception("Oversized serial response");}return lines.TryDequeue(out line);}
 public void Dispose(){if(serial!=null){serial.Close();serial.Dispose();}if(child!=null){try{child.StandardInput.Close();if(!child.WaitForExit(200))child.Kill();}finally{child.Dispose();}}}
}
public sealed class XiangqiBoard:Panel {
 public XiangqiBoard(){SetStyle(ControlStyles.UserPaint|ControlStyles.AllPaintingInWmPaint|ControlStyles.OptimizedDoubleBuffer|ControlStyles.ResizeRedraw,true);}
 public void ClickSquare(int square){OnMouseClick(new MouseEventArgs(MouseButtons.Left,1,48+(square%9)*56,48+(square/9)*56,0));}
}
public sealed class XiangqiWindow:Form {
 readonly XiangqiModel model=new XiangqiModel();readonly XiangqiBoard board=new XiangqiBoard();readonly Label state=new Label(),stats=new Label();readonly TextBox log=new TextBox();
 readonly ComboBox colour=new ComboBox(),thinking=new ComboBox();readonly Button fresh=new Button(),undo=new Button(),stop=new Button(),resume=new Button(),save=new Button(),load=new Button();
 readonly Timer timer=new Timer();readonly Stopwatch silence=new Stopwatch();XiangqiLink link;bool busy=true,started,suspended,loading,preview;int human,selected=-1,hover=-1;long hz=75000000;Queue<Point> replay=new Queue<Point>();
 public XiangqiWindow(string port,string exe,bool local,bool offline){
  preview=offline;Text=offline?"Xiangqi - OFFLINE UI PREVIEW":local?"Xiangqi - HOST TEST (AI runs on this PC)":"Xiangqi - FPGA "+port+" / 115200 8N1";
  ClientSize=new Size(1050,750);FormBorderStyle=FormBorderStyle.FixedSingle;MaximizeBox=false;Font=new Font("Segoe UI",10);
  state.SetBounds(12,12,1020,28);state.Text="Waiting for CPU / DDR initialization...";Controls.Add(state);
  string[] names={"New","Undo","Stop","Think","Save","Load"};Button[] buttons={fresh,undo,stop,resume,save,load};for(int i=0;i<6;i++){buttons[i].Text=names[i];buttons[i].SetBounds(12+i*86,45,80,28);Controls.Add(buttons[i]);}
  colour.DropDownStyle=ComboBoxStyle.DropDownList;colour.Items.AddRange(new object[]{"Red (New game)","Black (New game)"});colour.SelectedIndex=0;colour.SetBounds(545,45,150,28);Controls.Add(colour);
  thinking.DropDownStyle=ComboBoxStyle.DropDownList;thinking.Items.AddRange(new object[]{"100","500","1000","3000","5000"});thinking.SelectedItem="1000";thinking.SetBounds(705,45,100,28);Controls.Add(thinking);
  Label units=new Label();units.Text="ms / move";units.SetBounds(814,49,110,24);Controls.Add(units);
  board.SetBounds(12,85,550,610);board.BackColor=Color.FromArgb(226,185,120);board.Paint+=PaintBoard;board.MouseClick+=ClickBoard;
  board.MouseMove+=(s,e)=>SetHover(XiangqiModel.Cell(e.X,e.Y));board.MouseLeave+=(s,e)=>SetHover(-1);Controls.Add(board);
  stats.SetBounds(585,90,450,225);stats.Font=new Font("Consolas",10);stats.Text="FPGA search, DDR transposition table.\nNo completed search yet.";Controls.Add(stats);
  log.SetBounds(585,325,450,380);log.Multiline=true;log.ReadOnly=true;log.ScrollBars=ScrollBars.Vertical;log.Font=new Font("Consolas",9);Controls.Add(log);
  Label note=new Label();note.SetBounds(12,710,1020,28);note.Text="Click your piece, then destination. Red moves first. HOST TEST uses the PC, not the FPGA.";Controls.Add(note);
  fresh.Click+=(s,e)=>NewGame();undo.Click+=(s,e)=>{suspended=false;SendBusy("UNDO "+(model.Side==human?2:1));};stop.Click+=(s,e)=>{suspended=true;link.Send("STOP");};resume.Click+=(s,e)=>{suspended=false;Think();};save.Click+=SaveGame;load.Click+=LoadGame;
  thinking.SelectedIndexChanged+=(s,e)=>{if(link!=null&&!busy)link.Send("TIME "+thinking.Text);};timer.Interval=15;timer.Tick+=(s,e)=>Poll();
  FormClosed+=(s,e)=>{timer.Stop();if(link!=null)link.Dispose();timer.Dispose();};
  if(!offline){link=new XiangqiLink(port,exe,local);link.Send("PING");silence.Start();timer.Start();}UpdateControls();
 }
 void SetHover(int next){if(next==hover)return;int old=hover;hover=next;foreach(int p in new int[]{old,next})if(p>=0)board.Invalidate(new Rectangle(20+(p%9)*56,20+(p/9)*56,56,56));}
 void ClickBoard(object sender,MouseEventArgs e){
  int p=XiangqiModel.Cell(e.X,e.Y);if(busy||suspended||model.Side!=human||model.Outcome!=0||p<0)return;
  byte piece=model.Board[p];if(piece>0 && (piece<=7?0:1)==human){selected=p;board.Invalidate();return;}
  if(selected>=0){int from=selected;selected=-1;SendBusy("PLAY "+from+" "+p);board.Invalidate();}
 }
 void SendBusy(string s){busy=true;silence.Restart();link.Send(s);UpdateControls();}
 void NewGame(){loading=false;replay.Clear();human=colour.SelectedIndex;suspended=false;selected=-1;link.Send("TIME "+thinking.Text);SendBusy("NEW");}
 void Think(){if(model.Outcome==0){state.Text="Engine thinking...";SendBusy("GO");}}
 void UpdateControls(){fresh.Enabled=load.Enabled=colour.Enabled=thinking.Enabled=!busy;undo.Enabled=!busy&&model.Count>=2;stop.Enabled=busy&&started;resume.Enabled=!busy&&suspended&&model.Side!=human&&model.Outcome==0;save.Enabled=!busy&&model.Moves.Count==model.Count;}
 void Poll(){try{string line;int n=0;while(n++<512&&link.Read(out line))Receive(line);if(busy&&silence.ElapsedMilliseconds>15000)state.Text="Waiting for response. Check FPGA image, DDR-ready LED, COM port or board reset.";}catch(Exception e){timer.Stop();MessageBox.Show(e.Message,"Connection error");busy=false;UpdateControls();}}
 void Receive(string line){
  line=line.Trim();if(line.Length==0)return;
  if(line.Length!=9 || !Regex.IsMatch(line,"^[0-9A-E]{9}$")){log.AppendText(line+Environment.NewLine);if(log.TextLength>60000)log.Text=log.Text.Substring(log.TextLength-40000);}
  if(line.StartsWith("HELLO ")){Match h=Regex.Match(line,@"hz=(\d+)");if(h.Success)hz=long.Parse(h.Groups[1].Value);if(!started){started=true;if(!preview)NewGame();}return;}
  if(line.StartsWith("ERROR ")){loading=false;replay.Clear();busy=false;suspended=model.Side!=human;state.Text=line;UpdateControls();return;}
  if(line=="CANCELLED")suspended=true;
  if(line.StartsWith("INFO ")){
   Dictionary<string,double> v=new Dictionary<string,double>();foreach(Match m in Regex.Matches(line,@"(\w+)=(-?\d+)"))v[m.Groups[1].Value]=double.Parse(m.Groups[2].Value,System.Globalization.CultureInfo.InvariantCulture);
   double cycles=v["cycles"],nodes=v["nodes"],ms=cycles/hz*1000,nps=cycles>0?nodes*hz/cycles:0;
   stats.Text=String.Format(System.Globalization.CultureInfo.InvariantCulture,"Depth: {0}   Score: {1}\nNodes: {2:N0}   NPS: {3:N0}\nCompute: {4:F2} ms\nCycles: {5:N0}\nInstructions: {6:N0}\nIPC: {7}\nTT matches: {8} / {9}\nQ-nodes: {10}   Cutoffs: {11}\nDDR read/write: {12} / {13}\nDDR line hits: {14}\nDDR wait cycles: {15:N0} ({16:F1}%)\nStopped/budget: {17}\n{18}",v["depth"],v["score"],nodes,nps,ms,cycles,v["instret"],v["instret"]>0&&cycles>0?(v["instret"]/cycles).ToString("F3",System.Globalization.CultureInfo.InvariantCulture):"HOST: not measured",v["tt_hits"],v["tt_probes"],v["qnodes"],v["cutoffs"],v["ddr_reads"],v["ddr_writes"],v["ddr_hits"],v["ddr_wait"],cycles>0?100*v["ddr_wait"]/cycles:0,v["stopped"],preview?"Preview from captured HOST test":"Search ROI excludes reply transmission");
  }
  if(model.Feed(line)){
   busy=false;selected=-1;if(model.Side==human)suspended=false;board.Invalidate();
   state.Text=model.Outcome==1?"Red wins":model.Outcome==2?"Black wins":model.Outcome==3?"Draw":(model.Side==human?"Your turn":"Engine turn")+(model.Checked!=0?" - CHECK":"")+(suspended?" - paused":"")+"  |  Ply: "+model.Count;
   if(!preview){if(loading&&replay.Count>0){Point p=replay.Dequeue();SendBusy("PLAY "+p.X+" "+p.Y);}else{loading=false;if(!suspended&&model.Outcome==0&&model.Side!=human)Think();}}
   UpdateControls();
  }
 }
 void PaintBoard(object sender,PaintEventArgs e){
  Graphics g=e.Graphics;g.SmoothingMode=System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
  using(Pen pen=new Pen(Color.FromArgb(65,45,20),1)){
   for(int y=0;y<10;y++)g.DrawLine(pen,48,48+y*56,496,48+y*56);
   for(int x=0;x<9;x++){g.DrawLine(pen,48+x*56,48,48+x*56,272);g.DrawLine(pen,48+x*56,328,48+x*56,552);}
   g.DrawLine(pen,48,272,48,328);g.DrawLine(pen,496,272,496,328);
   foreach(int y in new int[]{0,7}){g.DrawLine(pen,216,48+y*56,328,160+y*56);g.DrawLine(pen,328,48+y*56,216,160+y*56);}
  }
  using(Font f=new Font("Segoe UI",9))for(int i=0;i<10;i++){g.DrawString((10-i).ToString(),f,Brushes.Black,18,40+i*56);if(i<9)g.DrawString(((char)('A'+i)).ToString(),f,Brushes.Black,42+i*56,18);}
  using(Font f=new Font("Microsoft YaHei",18)) {g.DrawString("楚河",f,Brushes.SaddleBrown,120,282);g.DrawString("汉界",f,Brushes.SaddleBrown,350,282);}
  string pieces=" 帅仕相马车炮兵将士象马车炮卒";
  using(Font f=new Font("Microsoft YaHei",23,FontStyle.Bold))using(Brush fill=new SolidBrush(Color.FromArgb(252,232,184)))using(StringFormat center=new StringFormat()){
   center.Alignment=StringAlignment.Center;center.LineAlignment=StringAlignment.Center;
   for(int i=0;i<90;i++){int v=model.Board[i];if(v==0)continue;int x=48+(i%9)*56,y=48+(i/9)*56;g.FillEllipse(fill,x-24,y-24,48,48);g.DrawEllipse(Pens.SaddleBrown,x-24,y-24,48,48);g.DrawString(pieces[v].ToString(),f,v<=7?Brushes.DarkRed:Brushes.Black,new RectangleF(x-25,y-26,50,52),center);}
  }
  if(model.Moves.Count>0){Point last=model.Moves[model.Moves.Count-1];foreach(int p in new int[]{last.X,last.Y})g.DrawRectangle(Pens.Red,22+(p%9)*56,22+(p/9)*56,52,52);}
  if(selected>=0)g.DrawEllipse(Pens.DarkOrange,21+(selected%9)*56,21+(selected/9)*56,54,54);
  if(!busy&&hover>=0)g.DrawRectangle(Pens.RoyalBlue,22+(hover%9)*56,22+(hover/9)*56,52,52);
 }
 void SaveGame(object sender,EventArgs e){using(SaveFileDialog d=new SaveFileDialog()){d.Filter="Xiangqi replay|*.xqg";if(d.ShowDialog()==DialogResult.OK)File.WriteAllText(d.FileName,model.Replay(human,thinking.Text),Encoding.UTF8);}}
 void LoadGame(object sender,EventArgs e){using(OpenFileDialog d=new OpenFileDialog()){d.Filter="Xiangqi replay|*.xqg";if(d.ShowDialog()!=DialogResult.OK)return;try{int who,budget;Queue<Point> q=XiangqiModel.ParseReplay(File.ReadAllLines(d.FileName),out who,out budget);human=who;colour.SelectedIndex=who;if(!thinking.Items.Contains(budget.ToString()))thinking.Items.Add(budget.ToString());thinking.SelectedItem=budget.ToString();loading=true;replay=q;suspended=false;link.Send("TIME "+budget);SendBusy("NEW");}catch(Exception ex){MessageBox.Show(ex.Message,"Replay error");}}}
 void ShowOffscreen(){StartPosition=FormStartPosition.Manual;Location=new Point(-20000,-20000);ShowInTaskbar=false;Show();Application.DoEvents();}
 void WaitFor(Func<bool> predicate){Stopwatch watch=Stopwatch.StartNew();while(!predicate()){Application.DoEvents();System.Threading.Thread.Sleep(5);if(watch.ElapsedMilliseconds>10000)throw new Exception("GUI timeout: "+state.Text);}}
 public static void TestHost(string exe){Application.EnableVisualStyles();using(XiangqiWindow w=new XiangqiWindow(null,exe,true,false)){
  w.ShowOffscreen();w.WaitFor(()=>w.started&&!w.busy&&w.model.Count==0);w.thinking.SelectedItem="100";
  w.board.ClickSquare(54);w.board.ClickSquare(45);w.WaitFor(()=>!w.busy&&w.model.Count==2);if(w.model.Board[45]!=7)throw new Exception("Human move not applied");
  w.undo.PerformClick();w.WaitFor(()=>!w.busy&&w.model.Count==0);w.colour.SelectedIndex=1;w.fresh.PerformClick();w.WaitFor(()=>!w.busy&&w.model.Count==1&&w.model.Side==1);
  w.thinking.SelectedItem="5000";w.board.ClickSquare(27);w.board.ClickSquare(36);w.WaitFor(()=>w.busy&&w.model.Count==2);w.stop.PerformClick();w.WaitFor(()=>!w.busy&&w.suspended);if(w.model.Count!=2)throw new Exception("Cancelled search committed a move");
  int who,budget;Queue<Point> q=XiangqiModel.ParseReplay(w.model.Replay(1,"100").Replace("\r","").Split('\n'),out who,out budget);if(q.Count!=2||who!=1||budget!=100)throw new Exception("Replay roundtrip failed");
  w.human=who;w.loading=true;w.replay=q;w.suspended=false;w.link.Send("TIME 100");w.SendBusy("NEW");w.WaitFor(()=>!w.busy&&w.model.Count==3);w.Hide();
 }}
 public static void Start(string port,string exe,bool local){Application.EnableVisualStyles();Application.Run(new XiangqiWindow(port,exe,local,false));}
 public static void Preview(string path,string trace){Application.EnableVisualStyles();using(XiangqiWindow w=new XiangqiWindow(null,null,false,true)){foreach(string line in File.ReadAllLines(trace))w.Receive(line);w.ShowOffscreen();using(Bitmap image=new Bitmap(w.Width,w.Height)){w.DrawToBitmap(image,new Rectangle(0,0,w.Width,w.Height));image.Save(path,System.Drawing.Imaging.ImageFormat.Png);}}}
}
