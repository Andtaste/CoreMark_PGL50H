// Uses existing XiangqiLink,XiangqiModel,GomokuModel,GomokuReview classes.
// One serial connection,one window,one timer and one game active at a time.
public sealed class BoardGamesWindow:Form {
 readonly Button fullscreenButton=new Button();
 readonly Dictionary<Control,Rectangle> layoutBounds=new Dictionary<Control,Rectangle>();
 readonly Dictionary<Control,Font> layoutFonts=new Dictionary<Control,Font>();
 readonly Dictionary<Control,Font> scaledFonts=new Dictionary<Control,Font>();
 bool fullscreen,layoutReady;Rectangle windowBounds;FormWindowState previousWindowState;
 readonly XiangqiLink link;readonly XiangqiBoard board=new XiangqiBoard();readonly Timer timer=new Timer();
 readonly ComboBox game=new ComboBox(),colour=new ComboBox(),budget=new ComboBox();
 readonly Button coremark=new Button();bool coremarkBusy;readonly Button select=new Button(),fresh=new Button(),undo=new Button(),stop=new Button(),think=new Button(),save=new Button(),load=new Button(),review=new Button(),prev=new Button(),next=new Button();
 readonly CheckBox assist=new CheckBox();readonly Button hintButton=new Button();
 readonly Label state=new Label(),stats=new Label();readonly TextBox log=new TextBox();
 GomokuModel gm=new GomokuModel();XiangqiModel xm=new XiangqiModel();GomokuReview gr;
 int active,human,selected=-1,hover=-1,hintAt=-1;Point? hintMove;bool hintBusy;bool busy,suspended,loading,reviewing;double hz=80000000;
 int loadPreviousHuman;bool loadPreviousSuspended;
 Queue<Point> replay=new Queue<Point>();List<Point> reviewMoves;int reviewStep;bool host;
 const string NoSearchStats="当前局面尚无搜索结果";
 readonly List<string> statsHistory=new List<string>{NoSearchStats};string pendingStats;bool undoBoardPending;
 readonly List<bool> checkHistory=new List<bool>{false};
 static readonly string[] pieces={"","帅","仕","相","马","车","炮","兵","将","士","象","马","车","炮","卒"};
 public BoardGamesWindow(string port,string exe,bool local){
  host=local;Text=local?"棋类平台 — HOST TEST（电脑计算）":"FPGA 棋类平台 — 自研RISC-V CPU";ClientSize=new Size(1070,760);AutoScaleMode=AutoScaleMode.None;FormBorderStyle=FormBorderStyle.Sizable;MaximizeBox=true;MinimumSize=new Size(820,620);Font=new Font("Microsoft YaHei UI",10);
  game.DropDownStyle=ComboBoxStyle.DropDownList;game.Items.AddRange(new object[]{"五子棋","中国象棋"});game.SelectedIndex=0;game.SetBounds(12,12,125,28);Controls.Add(game);
  select.Text="切换游戏";select.SetBounds(145,12,100,28);Controls.Add(select);
  colour.DropDownStyle=ComboBoxStyle.DropDownList;colour.Items.AddRange(new object[]{"执先手","执后手"});colour.SelectedIndex=0;colour.SetBounds(255,12,110,28);Controls.Add(colour);
  budget.DropDownStyle=ComboBoxStyle.DropDownList;budget.Items.AddRange(new object[]{"100","500","1000","3000","5000"});budget.SelectedItem="1000";budget.SetBounds(375,12,90,28);Controls.Add(budget);
  Label ms=new Label();ms.Text="毫秒/步";ms.SetBounds(475,16,90,24);Controls.Add(ms);
  Button[] buttons={fresh,undo,stop,think,save,load,review,prev,next};string[] names={"新局","悔棋","停止","继续AI思考","保存棋谱","载入棋谱","复盘/返回","上一步","下一步"};
  for(int i=0;i<buttons.Length;i++){buttons[i].Text=names[i];buttons[i].SetBounds(12+i*115,48,108,28);Controls.Add(buttons[i]);}
  state.SetBounds(575,12,480,30);state.Text="正在连接...";Controls.Add(state);
  board.SetBounds(12,90,590,620);board.BackColor=Color.FromArgb(231,194,138);board.Paint+=PaintBoard;board.MouseClick+=(s,e)=>{Point p=BoardPoint(e.X,e.Y);ClickAt(p.X,p.Y);};board.MouseMove+=(s,e)=>{Point p=BoardPoint(e.X,e.Y);SetHover(Cell(p.X,p.Y));};board.MouseLeave+=(s,e)=>SetHover(-1);
  Controls.Add(board);
  assist.Text="辅助模式";assist.SetBounds(620,92,125,28);Controls.Add(assist);hintButton.Text="推荐一步";hintButton.SetBounds(760,90,120,28);Controls.Add(hintButton);
  assist.CheckedChanged+=(s,e)=>{hintMove=null;hintAt=-1;if(assist.Checked)RequestHint();board.Invalidate();UpdateControls();};hintButton.Click+=(s,e)=>RequestHint();
  coremark.Text="CoreMark（约15秒）";coremark.SetBounds(890,90,165,28);Controls.Add(coremark);
  coremark.Click+=(sender,e)=>{if(busy)return;coremarkBusy=true;SendBusy("COREMARK");state.Text="CoreMark运行中，完成后返回原对局";};
  stats.SetBounds(620,132,435,225);stats.Font=new Font("Consolas",11);stats.Text="请选择游戏，并点击“切换游戏”";Controls.Add(stats);
  log.SetBounds(620,365,435,345);log.Multiline=true;log.ReadOnly=true;log.ScrollBars=ScrollBars.Vertical;log.Font=new Font("Consolas",9);Controls.Add(log);
  Label note=new Label();note.SetBounds(12,720,885,30);note.Text="同一下载镜像切换两种棋。切换会开始新局；请先保存棋谱。搜索时先停止，再切换。";Controls.Add(note);
  fullscreenButton.Text="全屏 F11";fullscreenButton.SetBounds(910,720,145,30);fullscreenButton.Click+=(s,e)=>ToggleFullscreen();Controls.Add(fullscreenButton);
  select.Click+=(s,e)=>SelectGame();fresh.Click+=(s,e)=>NewGame();undo.Click+=(s,e)=>{suspended=false;SendBusy("UNDO "+Math.Min(Count,Side==HumanSide?2:1));};stop.Click+=(s,e)=>{suspended=true;link.Send("STOP");};think.Click+=(s,e)=>{suspended=false;Think();};
  save.Click+=SaveGame;load.Click+=LoadGame;review.Click+=(s,e)=>ToggleReview();prev.Click+=(s,e)=>ReviewJump(reviewStep-1);next.Click+=(s,e)=>ReviewJump(reviewStep+1);
  budget.SelectedIndexChanged+=(s,e)=>{if(link!=null&&!busy&&active!=0)link.Send("TIME "+budget.Text);};
  link=new XiangqiLink(port,exe,local);link.Send("PING");timer.Interval=15;timer.Tick+=(s,e)=>Poll();timer.Start();
  KeyPreview=true;KeyDown+=(s,e)=>{if(e.KeyCode==Keys.F11||(fullscreen&&e.KeyCode==Keys.Escape)){ToggleFullscreen();e.Handled=true;e.SuppressKeyPress=true;return;}if(reviewing&&(e.KeyCode==Keys.Left||e.KeyCode==Keys.Right)){ReviewJump(reviewStep+(e.KeyCode==Keys.Left?-1:1));e.Handled=true;}};
  foreach(Control c in Controls){layoutBounds[c]=c.Bounds;layoutFonts[c]=c.Font;}
  layoutReady=true;Resize+=(s,e)=>ResizeLayout();ResizeLayout();
  FormClosed+=(s,e)=>{timer.Stop();link.Dispose();timer.Dispose();foreach(Font f in scaledFonts.Values)f.Dispose();};UpdateControls();
 }
 void ToggleFullscreen(){
  if(!fullscreen){previousWindowState=WindowState;windowBounds=WindowState==FormWindowState.Normal?Bounds:RestoreBounds;Rectangle screen=Screen.FromControl(this).Bounds;fullscreen=true;WindowState=FormWindowState.Normal;FormBorderStyle=FormBorderStyle.None;Bounds=screen;}
  else{fullscreen=false;WindowState=FormWindowState.Normal;FormBorderStyle=FormBorderStyle.Sizable;Bounds=windowBounds;WindowState=previousWindowState;}
  fullscreenButton.Text=fullscreen?"退出全屏 Esc":"全屏 F11";ResizeLayout();
 }
 void ResizeLayout(){
  if(!layoutReady||WindowState==FormWindowState.Minimized)return;
  float sx=ClientSize.Width/1070f,sy=ClientSize.Height/760f,scale=Math.Min(sx,sy);
  SuspendLayout();
  foreach(Control c in Controls){Rectangle r=layoutBounds[c];c.Bounds=new Rectangle((int)Math.Round(r.X*sx),(int)Math.Round(r.Y*sy),(int)Math.Round(r.Width*sx),(int)Math.Round(r.Height*sy));Font original=layoutFonts[c];float size=original.Size*scale;
   if(Math.Abs(c.Font.Size-size)>.05){Font old;scaledFonts.TryGetValue(c,out old);Font next=new Font(original.FontFamily,size,original.Style);c.Font=next;scaledFonts[c]=next;if(old!=null)old.Dispose();}
  }
  ResumeLayout();board.Invalidate();
 }
 float BoardScale {get{return Math.Min(board.ClientSize.Width/590f,board.ClientSize.Height/620f);}}
 PointF BoardOrigin {get{float scale=BoardScale;return new PointF((board.ClientSize.Width-590*scale)/2,(board.ClientSize.Height-620*scale)/2);}}
 Point BoardPoint(int x,int y){PointF o=BoardOrigin;float scale=BoardScale;return new Point((int)Math.Round((x-o.X)/scale),(int)Math.Round((y-o.Y)/scale));}
 bool HasHint {get{return hintMove.HasValue;}}
 int HumanSide {get{return active==1?human+1:human;}}int Side {get{return active==1?gm.Side:xm.Side;}}int Count {get{return active==1?gm.Count:xm.Count;}}int Outcome {get{return active==1?(gm.Winner!=0?gm.Winner:gm.Count==225?3:0):xm.Outcome;}}
 List<Point> Moves {get{return active==1?gm.Moves:xm.Moves;}}
 void SendBusy(string s){if(s.StartsWith("PLAY ")||s.StartsWith("UNDO ")||s=="NEW"||s.StartsWith("SELECT ")||s.StartsWith("FEN ")){hintMove=null;hintAt=-1;selected=-1;hover=-1;board.Invalidate();}busy=true;link.Send(s);UpdateControls();}
 void SelectGame(){if(busy)return;suspended=false;reviewing=false;loading=false;replay.Clear();SendBusy("SELECT "+(game.SelectedIndex==0?"GOMOKU":"XIANGQI"));}
 void NewGame(){human=colour.SelectedIndex;reviewing=false;loading=false;suspended=false;selected=-1;link.Send("TIME "+budget.Text);SendBusy("NEW");}
 void Think(){if(active!=0&&Outcome==0&&Side!=HumanSide){SendBusy("GO");state.Text="FPGA正在搜索...";}}
 void RequestHint(){if(!assist.Checked||active==0||busy||reviewing||Side!=HumanSide||Outcome!=0)return;hintMove=null;hintAt=Count;hintBusy=true;SendBusy("HINT");state.Text="FPGA正在为你推荐走法（不会自动落子）...";}
 void SetHover(int cell){if(cell==hover)return;hover=cell;board.Invalidate();}
 void UpdateControls(){coremark.Enabled=!busy&&!reviewing;select.Enabled=game.Enabled=colour.Enabled=budget.Enabled=!busy&&!reviewing;fresh.Enabled=active!=0&&!busy&&!reviewing;undo.Enabled=active!=0&&!busy&&!reviewing&&Count>0;stop.Enabled=busy&&active!=0&&!coremarkBusy;think.Enabled=active!=0&&!busy&&!reviewing&&Outcome==0&&Side!=HumanSide;save.Enabled=active!=0&&!busy;load.Enabled=active!=0&&!busy&&!reviewing;review.Enabled=active!=0&&!busy;prev.Enabled=reviewing&&reviewStep>0;next.Enabled=reviewing&&reviewStep<reviewMoves.Count;assist.Enabled=!busy&&!reviewing;hintButton.Enabled=assist.Checked&&active!=0&&!busy&&!reviewing&&Side==HumanSide&&Outcome==0;review.Text=reviewing?"返回对局":"复盘";}
 void Poll(){try{string line;int n=0;while(n++<100&&link.Read(out line))Receive(line);}catch(Exception ex){timer.Stop();busy=true;UpdateControls();state.Text="连接/协议错误";MessageBox.Show(ex.Message,"棋类平台");}}
 public void Receive(string line){
  if(line.Length==0)return;if(log.TextLength>20000)log.Clear();log.AppendText(line+Environment.NewLine);
  if(line.StartsWith("COREMARK END ")){coremarkBusy=false;busy=false;state.Text=line.Contains("crc=PASS")?"CoreMark CRC通过，详情见日志":"CoreMark CRC失败";UpdateControls();return;}
  if(line.StartsWith("HELLO ")){
   Match f=Regex.Match(line,@"hz=(\d+)");if(f.Success)hz=double.Parse(f.Groups[1].Value);
   int id=line.Contains("GOMOKU_V1")?1:line.Contains("XIANGQI_V1")?2:0;
   if(id!=active||busy){if(id!=0)human=colour.SelectedIndex;active=id;gm=new GomokuModel();xm=new XiangqiModel();selected=-1;hover=-1;hintMove=null;hintAt=-1;hintBusy=false;reviewing=false;ResetStatistics();}
   state.Text=host?"HOST TEST：电脑计算":"FPGA："+(hz/1000000).ToString("F0")+" MHz";
   if(active==0){busy=false;stats.Text="请选择游戏，并点击“切换游戏”";state.Text+="，请选择游戏";board.Invalidate();UpdateControls();}else link.Send("TIME "+budget.Text);
   return;
  }
  if(line.StartsWith("ERROR ")){if(loading){human=loadPreviousHuman;colour.SelectedIndex=human;suspended=loadPreviousSuspended;}xm.CancelFen();bool wasHint=hintBusy;hintBusy=false;hintMove=null;busy=false;loading=false;pendingStats=null;undoBoardPending=false;RestoreStatistics(Count);state.Text=line=="ERROR DDR_NOT_READY"?"DDR尚未就绪，可先运行五子棋":wasHint&&line=="ERROR COMMAND"?"此FPGA镜像不支持辅助模式，请下载新版镜像":line;UpdateControls();return;}
  if(line=="CANCELLED"){suspended=true;if(hintBusy)hintMove=null;}
  if(line.StartsWith("HINT ")){string[] a=line.Split(' ');if(!hintBusy||a.Length!=4||int.Parse(a[1])!=HumanSide)throw new Exception("Unexpected hint");int x=int.Parse(a[2]),y=int.Parse(a[3]);if(active==1?(x<0||x>=15||y<0||y>=15||gm.Board[x,y]!=0):(x<0||x>=90||y<0||y>=90||xm.Board[x]==0))throw new Exception("Invalid hint");hintMove=new Point(x,y);return;}
  if(line.StartsWith("INFO "))ShowStats(line);
  if(active==0)return;
  if(line=="OK NEW"||line=="OK FEN")ResetStatistics();
  if(line.StartsWith("OK UNDO ")){undoBoardPending=true;pendingStats=null;}
  bool done=active==1?gm.Feed(line):xm.Feed(line);
  if(done){bool finishedUndo=undoBoardPending;undoBoardPending=false;CaptureBoardStatistics();bool finishedHint=hintBusy;hintBusy=false;busy=false;if(!reviewing&&!loading&&Side==HumanSide)suspended=false;board.Invalidate();state.Text=(active==1?"五子棋":"中国象棋")+"：第"+Count+"步"+(Outcome==0?(Side==HumanSide?"，轮到你":"，轮到AI"):Outcome==3?"，平局":Outcome==human+1?"，你赢了":"，AI获胜");
   if(loading&&replay.Count>0){Point p=replay.Dequeue();SendBusy("PLAY "+p.X+" "+p.Y);}
   else{if(loading)suspended=Side!=HumanSide;loading=false;if(finishedHint){state.Text+=hintMove.HasValue?"，绿色标记为AI推荐":"，推荐已停止";}else if(!suspended&&!reviewing&&Outcome==0&&Side!=HumanSide)Think();else if(!finishedUndo&&assist.Checked&&!reviewing&&Outcome==0&&Side==HumanSide&&hintAt!=Count)RequestHint();}
   if(active==2&&xm.Checked!=0&&Outcome==0)state.Text+="，"+(xm.Side==0?"红方":"黑方")+"被将军";
   UpdateControls();
  }
 }
 void ShowStats(string line){Dictionary<string,double> v=new Dictionary<string,double>();foreach(Match m in Regex.Matches(line,@"(\w+)=(-?\d+)"))v[m.Groups[1].Value]=double.Parse(m.Groups[2].Value,System.Globalization.CultureInfo.InvariantCulture);
  double c=v["cycles"],i=v["instret"];stats.Text=String.Format(System.Globalization.CultureInfo.InvariantCulture,"Depth: {0}   Score: {1}\nNodes: {2:N0}\nCompute: {3:F3} ms\nCycles: {4:N0}\nInstructions: {5:N0}\nIPC: {6}\nTT hits: {7:N0}\nCutoffs: {8:N0}\nDDR wait: {9:N0}\n{10}",v["depth"],v["score"],v["nodes"],c/hz*1000,c,i,i>0&&c>0?(i/c).ToString("F3",System.Globalization.CultureInfo.InvariantCulture):"HOST: not measured",v["tt_hits"],v["cutoffs"],v["ddr_wait"],host?"HOST TEST — PC executes AI":"FPGA search;reply transmission excluded");
  // INFO precedes MOVE/HINT/BOARD. Associate it only after END_BOARD validates
  // the resulting position, not with the old Count at INFO reception time.
  pendingStats=stats.Text;
 }
 void ResetStatistics(){statsHistory.Clear();statsHistory.Add(NoSearchStats);checkHistory.Clear();checkHistory.Add(false);pendingStats=null;undoBoardPending=false;stats.Text=NoSearchStats;}
 void RestoreStatistics(int step){stats.Text=step>=0&&step<statsHistory.Count?statsHistory[step]:NoSearchStats;}
 void CaptureBoardStatistics(){
  // Human moves inherit the last available search. Undo discards the old
  // continuation so a new branch never reuses future-position measurements.
  while(statsHistory.Count<=Count)statsHistory.Add(statsHistory[statsHistory.Count-1]);
  if(statsHistory.Count>Count+1)statsHistory.RemoveRange(Count+1,statsHistory.Count-Count-1);
  while(checkHistory.Count<=Count)checkHistory.Add(false);
  if(checkHistory.Count>Count+1)checkHistory.RemoveRange(Count+1,checkHistory.Count-Count-1);
  checkHistory[Count]=active==2&&xm.Checked!=0&&Outcome==0;
  if(pendingStats!=null)statsHistory[Count]=pendingStats;
  pendingStats=null;RestoreStatistics(reviewing?reviewStep:Count);
 }
 string BoardResultText {get{int result=Outcome;if(active==0||result==0||result==3||(reviewing&&reviewStep!=Count))return null;return result==human+1?"获胜":"落败";}}
 Color BoardResultColor {get{return BoardResultText=="获胜"?Color.Red:Color.Black;}}
 bool DisplayedCheck {get{return active==2&&(reviewing?(reviewStep<checkHistory.Count&&checkHistory[reviewStep]):xm.Checked!=0&&Outcome==0);}}
 int CheckedKingSquare {get{if(!DisplayedCheck)return -1;byte king=(byte)((reviewing?(xm.InitialSide+reviewStep)%2:xm.Side)==0?1:8);byte[] position=reviewing?ReviewXiangqi():xm.Board;return Array.IndexOf(position,king);}}
 int Cell(int x,int y){if(active==1){Point p=GomokuModel.Cell(x,y);return p.X<0?-1:p.Y*15+p.X;}return active==2?XiangqiModel.Cell(x,y):-1;}
 void ClickAt(int x,int y){int p=Cell(x,y);if(active==0||p<0||busy||reviewing||suspended||Side!=HumanSide||Outcome!=0)return;
  if(active==1){if(gm.Board[p%15,p/15]==0)SendBusy("PLAY "+p%15+" "+p/15);return;}
  byte own=xm.Board[p];if(own>0&&(own<=7?0:1)==human){selected=p;board.Invalidate();return;}
  if(selected>=0){int from=selected;selected=-1;SendBusy("PLAY "+from+" "+p);}
 }
 void PaintBoard(object sender,PaintEventArgs e){Graphics g=e.Graphics;PointF origin=BoardOrigin;g.TranslateTransform(origin.X,origin.Y);g.ScaleTransform(BoardScale,BoardScale);g.SmoothingMode=System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
  if(active==0){g.DrawString("请选择五子棋或中国象棋",Font,Brushes.Black,100,250);return;}
  if(active==1){for(int k=0;k<15;k++){g.DrawLine(Pens.SaddleBrown,48,48+k*36,552,48+k*36);g.DrawLine(Pens.SaddleBrown,48+k*36,48,48+k*36,552);}
   foreach(Point star in new Point[]{new Point(3,3),new Point(11,3),new Point(7,7),new Point(3,11),new Point(11,11)})g.FillEllipse(Brushes.SaddleBrown,45+star.X*36,45+star.Y*36,6,6);
   byte[,] b=reviewing?gr.Board:gm.Board;for(int y=0;y<15;y++)for(int x=0;x<15;x++)if(b[x,y]!=0){Rectangle box=new Rectangle(33+x*36,33+y*36,30,30);g.FillEllipse(b[x,y]==1?Brushes.Black:Brushes.Ivory,box);g.DrawEllipse(Pens.Gray,box);}
   List<Point> ms=reviewing?reviewMoves:gm.Moves;int count=reviewing?reviewStep:ms.Count;if(count>0){Point last=ms[count-1];g.DrawEllipse(Pens.Red,31+last.X*36,31+last.Y*36,34,34);}
  }else{
   for(int y=0;y<10;y++)g.DrawLine(Pens.SaddleBrown,48,48+y*56,496,48+y*56);
   for(int x=0;x<9;x++){if(x==0||x==8)g.DrawLine(Pens.SaddleBrown,48+x*56,48,48+x*56,552);else{g.DrawLine(Pens.SaddleBrown,48+x*56,48,48+x*56,272);g.DrawLine(Pens.SaddleBrown,48+x*56,328,48+x*56,552);}}
   for(int palace=0;palace<2;palace++){int y=48+palace*7*56;g.DrawLine(Pens.SaddleBrown,216,y,328,y+112);g.DrawLine(Pens.SaddleBrown,328,y,216,y+112);}
   g.DrawString("楚 河                汉 界",Font,Brushes.SaddleBrown,130,285);
   byte[] b=reviewing?ReviewXiangqi():xm.Board;
   using(Font f=new Font("Microsoft YaHei UI",20,FontStyle.Bold))for(int p=0;p<90;p++)if(b[p]!=0)DrawChessPiece(g,p,b[p],f,255);
   List<Point> ms=reviewing?reviewMoves:xm.Moves;int count=reviewing?reviewStep:ms.Count;if(count>0){Point last=ms[count-1];foreach(int p in new int[]{last.X,last.Y})using(Pen pen=new Pen(Color.Firebrick,2))g.DrawEllipse(pen,22+p%9*56,22+p/9*56,52,52);}
  }
  if(!reviewing&&hintMove.HasValue&&assist.Checked){Point m=hintMove.Value;using(Pen pen=new Pen(Color.ForestGreen,3)){if(active==1)g.DrawEllipse(pen,31+m.X*36,31+m.Y*36,34,34);else{Point a=new Point(48+m.X%9*56,48+m.X/9*56),b=new Point(48+m.Y%9*56,48+m.Y/9*56);pen.EndCap=System.Drawing.Drawing2D.LineCap.ArrowAnchor;g.DrawLine(pen,a,b);g.DrawEllipse(pen,b.X-26,b.Y-26,52,52);}}}
  if(!reviewing&&selected>=0&&active==2)using(Pen pen=new Pen(Color.DarkOrange,3))g.DrawEllipse(pen,20+selected%9*56,20+selected/9*56,56,56);
  if(!reviewing&&!busy&&Side==HumanSide&&Outcome==0&&hover>=0){
   if(active==1&&gm.Board[hover%15,hover/15]==0){Rectangle box=new Rectangle(33+hover%15*36,33+hover/15*36,30,30);using(Brush fill=new SolidBrush(Color.FromArgb(125,gm.Side==1?Color.Black:Color.Ivory)))using(Pen pen=new Pen(Color.FromArgb(110,Color.DimGray),1)){g.FillEllipse(fill,box);g.DrawEllipse(pen,box);}}
   else if(active==2){byte target=xm.Board[hover];if(selected>=0&&hover!=selected&&(target==0||(target<=7?0:1)!=human)){using(Font f=new Font("Microsoft YaHei UI",20,FontStyle.Bold))DrawChessPiece(g,hover,xm.Board[selected],f,125);}else using(Pen pen=new Pen(Color.RoyalBlue,2))g.DrawEllipse(pen,22+hover%9*56,22+hover/9*56,52,52);}
  }
  DrawCheckNotice(g);DrawBoardResult(g);
 }
 void DrawCheckNotice(Graphics g){int square=CheckedKingSquare;if(square<0||BoardResultText!=null)return;
  using(Pen ring=new Pen(Color.Crimson,3)){
   g.DrawEllipse(ring,18+square%9*56,18+square/9*56,60,60);
   g.DrawEllipse(ring,22+square%9*56,22+square/9*56,52,52);
  }
  // Keep below the last rank, including piece radii, so no piece is covered.
  RectangleF area=new RectangleF(101,578,342,40);int side=reviewing?(xm.InitialSide+reviewStep)%2:xm.Side;
  using(Brush backdrop=new SolidBrush(Color.FromArgb(240,Color.Ivory)))using(Font font=new Font("Microsoft YaHei UI",20,FontStyle.Bold))using(StringFormat format=new StringFormat()){
   format.Alignment=StringAlignment.Center;format.LineAlignment=StringAlignment.Center;g.FillRectangle(backdrop,area);g.DrawString("将军 · "+(side==0?"红方":"黑方")+"应将",font,Brushes.Crimson,area,format);
  }
 }
 void DrawBoardResult(Graphics g){string result=BoardResultText;if(result==null)return;
  RectangleF area=new RectangleF(55,(620-150)/2f,590-110,150);
  using(Brush backdrop=new SolidBrush(Color.FromArgb(220,Color.Ivory)))using(Brush ink=new SolidBrush(BoardResultColor))using(Font font=new Font("Microsoft YaHei UI",64,FontStyle.Bold))using(StringFormat format=new StringFormat()){
   format.Alignment=StringAlignment.Center;format.LineAlignment=StringAlignment.Center;g.FillRectangle(backdrop,area);g.DrawString(result,font,ink,area,format);
  }
 }
 void DrawChessPiece(Graphics g,int square,byte piece,Font font,int alpha){Rectangle box=new Rectangle(24+square%9*56,24+square/9*56,48,48);using(Brush fill=new SolidBrush(Color.FromArgb(alpha,Color.Wheat)))using(Brush text=new SolidBrush(Color.FromArgb(alpha,piece<=7?Color.Firebrick:Color.Black)))using(Pen rim=new Pen(Color.FromArgb(alpha,Color.SaddleBrown)))using(StringFormat format=new StringFormat()){format.Alignment=StringAlignment.Center;format.LineAlignment=StringAlignment.Center;g.FillEllipse(fill,box);g.DrawEllipse(rim,box);g.DrawString(pieces[piece],font,text,box,format);}}
 byte[] ReviewXiangqi(){byte[] b=(byte[])xm.InitialBoard.Clone();for(int i=0;i<reviewStep;i++){Point p=reviewMoves[i];b[p.Y]=b[p.X];b[p.X]=0;}return b;}
 void ToggleReview(){if(!reviewing){reviewMoves=new List<Point>(Moves);reviewStep=0;selected=-1;hover=-1;if(active==1)gr=new GomokuReview(reviewMoves,"Current game");reviewing=true;suspended=true;if(active==1)gr.Jump(0);state.Text="复盘 0 / "+reviewMoves.Count+"（左右方向键或上一步/下一步）";}else{reviewing=false;if(Side==HumanSide)suspended=false;state.Text="已返回当前对局：第"+Count+"步";}RestoreStatistics(reviewing?reviewStep:Count);board.Invalidate();UpdateControls();}
 void ReviewJump(int step){if(!reviewing||step<0||step>reviewMoves.Count)return;reviewStep=step;if(active==1)gr.Jump(step);RestoreStatistics(step);state.Text="复盘 "+step+" / "+reviewMoves.Count;board.Invalidate();UpdateControls();}
 void SaveGame(object sender,EventArgs e){using(SaveFileDialog d=new SaveFileDialog()){d.Filter=active==1?"Gomoku|*.gmk":"Xiangqi|*.xqg";if(d.ShowDialog()!=DialogResult.OK)return;File.WriteAllText(d.FileName,active==1?GomokuModel.EncodeReplay(gm.Moves,human+1,budget.Text):xm.Replay(human,budget.Text));}}
 void LoadGame(object sender,EventArgs e){using(OpenFileDialog d=new OpenFileDialog()){d.Filter=active==1?"Gomoku|*.gmk":"象棋棋谱 / FEN残局|*.xqg;*.fen|象棋棋谱|*.xqg|FEN残局|*.fen";if(d.ShowDialog()!=DialogResult.OK)return;try{LoadReplayFile(d.FileName);}catch(Exception ex){MessageBox.Show(ex.Message,"棋谱");}}}
 void LoadReplayFile(string path){
  int who,ms;string fen=null;Queue<Point> moves;
  if(active==1)moves=GomokuModel.ParseReplay(File.ReadAllLines(path),out who,out ms);
  else if(String.Equals(Path.GetExtension(path),".fen",StringComparison.OrdinalIgnoreCase)){byte[] b;fen=XiangqiModel.ParseFen(File.ReadAllText(path),out b,out who);ms=int.Parse(budget.Text);moves=new Queue<Point>();}
  else moves=XiangqiModel.ParseReplay(File.ReadAllLines(path),out who,out ms,out fen);
  loadPreviousHuman=human;loadPreviousSuspended=suspended;human=active==1?who-1:who;colour.SelectedIndex=human;
  if(!budget.Items.Contains(ms.ToString()))budget.Items.Add(ms.ToString());budget.SelectedItem=ms.ToString();link.Send("TIME "+ms);
  replay=moves;loading=true;suspended=true;reviewing=false;
  SendBusy(fen==null?"NEW":"FEN "+xm.PrepareFen(fen));
 }
 void TestFenLoading(Action<Func<bool>> wait){
  string dir=Path.Combine(Path.GetTempPath(),"yixin-fen-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(dir);
  string file=Path.Combine(dir,"test.fen"),saved=Path.Combine(dir,"saved.xqg");
  try{
   assist.Checked=false;
   string fen="3a1k3/4a4/6R2/8R/2r6/9/9/1r7/4A4/3K1A3 w - - 0 1";
   File.WriteAllText(file,fen);LoadReplayFile(file);wait(()=>!busy);
   if(xm.Count!=0||xm.InitialSide!=0||xm.Board[24]!=5||xm.Board[3]!=9||suspended)throw new Exception("FEN initial state");
   byte[] initial=(byte[])xm.Board.Clone();assist.Checked=true;wait(()=>!busy&&HasHint);
   if(xm.Count!=0)throw new Exception("FEN hint changed position");assist.Checked=false;
   suspended=true;SendBusy("PLAY 24 6");wait(()=>!busy&&xm.Count==1);
   File.WriteAllText(saved,xm.Replay(0,"100"));LoadReplayFile(saved);wait(()=>!busy&&!loading);
   if(xm.Count!=1||xm.Board[6]!=5||xm.InitialFen==null||!suspended)throw new Exception("FEN save/load or unwanted AI move");
   ToggleReview();for(int i=0;i<90;i++)if(ReviewXiangqi()[i]!=initial[i])throw new Exception("FEN replay origin");ReviewJump(1);if(ReviewXiangqi()[6]!=5)throw new Exception("FEN replay move");ToggleReview();
   undo.PerformClick();wait(()=>!busy&&xm.Count==0);for(int i=0;i<90;i++)if(xm.Board[i]!=initial[i])throw new Exception("FEN undo");
   // A syntactically valid but illegal position: non-moving black king is checked.
   File.WriteAllText(file,"3a1kR2/4a4/9/8R/2r6/9/9/1r7/4A4/3K1A3 w");LoadReplayFile(file);wait(()=>!busy);
   if(!state.Text.Contains("ERROR FEN")||xm.Board[24]!=5||xm.InitialFen.Contains("3a1kR2"))throw new Exception("Rejected FEN modified live state");
   File.WriteAllText(file,"3a1kR2/4a4/9/8R/2r6/9/9/1r7/4A4/3K1A3 b");LoadReplayFile(file);wait(()=>!busy);
   if(xm.Side!=1||xm.InitialSide!=1||human!=1||xm.Checked!=1||CheckedKingSquare!=5)throw new Exception("Black-to-move FEN");
   assist.Checked=true;wait(()=>!busy&&HasHint);if(xm.Count!=0)throw new Exception("Black FEN hint committed move");assist.Checked=false;
   suspended=true;SendBusy("PLAY 5 14");wait(()=>!busy&&xm.Count==1);
   File.WriteAllText(saved,xm.Replay(1,"100"));LoadReplayFile(saved);wait(()=>!busy&&!loading);
   if(xm.InitialSide!=1||xm.Side!=0||xm.Count!=1)throw new Exception("Black FEN replay parity");
   ToggleReview();if(CheckedKingSquare!=5)throw new Exception("Black FEN review king");ReviewJump(1);if(DisplayedCheck)throw new Exception("Black FEN review evasion");ToggleReview();
   undo.PerformClick();wait(()=>!busy&&xm.Count==0);if(xm.Side!=1||xm.Checked!=1)throw new Exception("Black FEN undo");
   colour.SelectedIndex=0;NewGame();wait(()=>!busy);if(xm.InitialFen!=null||xm.Side!=0||xm.Board[0]!=12)throw new Exception("New game after FEN");
  }finally{File.Delete(file);File.Delete(saved);Directory.Delete(dir);}
 }
 public static void Start(string port,string exe,bool local){Application.EnableVisualStyles();Application.Run(new BoardGamesWindow(port,exe,local));}
 public static void TestHost(string exe,string screenshot){
  Application.EnableVisualStyles();using(BoardGamesWindow w=new BoardGamesWindow(null,exe,true)){
   w.ShowInTaskbar=false;w.StartPosition=FormStartPosition.Manual;w.Location=new Point(-3000,-3000);w.Show();w.suspended=true;
   Action<Func<bool>> wait=(condition)=>{Stopwatch s=Stopwatch.StartNew();while(!condition()){Application.DoEvents();System.Threading.Thread.Sleep(5);if(s.ElapsedMilliseconds>20000)throw new Exception("UI timeout: "+w.log.Text);}};
   wait(()=>w.state.Text.Contains("选择"));w.budget.SelectedItem="100";w.SelectGame();wait(()=>w.active==1&&!w.busy);
   w.coremark.PerformClick();wait(()=>!w.busy);if(!w.log.Text.Contains("COREMARK END crc=PASS valid=NO_HOST_TEST")||w.gm.Count!=0)throw new Exception("CoreMark UI/return failed");
   w.assist.Checked=true;wait(()=>!w.busy&&w.HasHint);if(w.gm.Count!=0)throw new Exception("Gomoku hint committed a move");
   w.SetHover(112);if(w.hover!=112)throw new Exception("Hover preview missing");
   if(!String.IsNullOrEmpty(screenshot)){using(Bitmap b=new Bitmap(w.Width,w.Height)){w.DrawToBitmap(b,new Rectangle(0,0,w.Width,w.Height));b.Save(screenshot+".gomoku-black.png",System.Drawing.Imaging.ImageFormat.Png);}}if(w.gm.Count!=0||w.gm.Board[7,7]!=0)throw new Exception("Black preview changed board");w.ClickAt(300,300);wait(()=>!w.busy&&w.gm.Count==2&&w.HasHint);
   string gomokuStats=w.stats.Text;w.ToggleReview();if(w.reviewStep!=0||w.gr.Cursor!=0)throw new Exception("Review start");w.ReviewJump(1);if(!w.reviewing||w.gr.Cursor!=1||w.stats.Text!=w.statsHistory[1])throw new Exception("Gomoku review");w.ToggleReview();if(w.stats.Text!=gomokuStats)throw new Exception("Review did not restore live statistics");
   int empty=0;while(w.gm.Board[empty%15,empty/15]!=0)empty++;w.ClickAt(48+empty%15*36,48+empty/15*36);wait(()=>!w.busy&&w.gm.Count==4&&w.HasHint);
   w.undo.PerformClick();wait(()=>!w.busy&&w.gm.Count==2);if(w.stats.Text!=gomokuStats||w.statsHistory.Count!=3||w.HasHint)throw new Exception("Gomoku undo statistics/continuation mismatch");
   w.assist.Checked=false;w.game.SelectedIndex=1;w.SelectGame();wait(()=>w.active==2&&!w.busy);w.assist.Checked=true;wait(()=>!w.busy&&w.HasHint);
   if(w.xm.Count!=0||w.xm.Moves.Count!=0)throw new Exception("Xiangqi hint committed a move");
   w.ClickAt(48,48+6*56);if(w.selected!=54)throw new Exception("Selected piece missing");w.SetHover(45);
   if(!String.IsNullOrEmpty(screenshot)){using(Bitmap b=new Bitmap(w.Width,w.Height)){w.DrawToBitmap(b,new Rectangle(0,0,w.Width,w.Height));b.Save(screenshot+".xiangqi.png",System.Drawing.Imaging.ImageFormat.Png);}}
   w.ClickAt(48,48+5*56);wait(()=>!w.busy&&w.xm.Count==2&&w.HasHint);byte[] live=(byte[])w.xm.Board.Clone();string xiangqiStats=w.stats.Text;
   w.SendBusy("PLAY 56 47");wait(()=>!w.busy&&w.xm.Count==4&&w.HasHint);w.undo.PerformClick();wait(()=>!w.busy&&w.xm.Count==2);if(w.stats.Text!=xiangqiStats||w.statsHistory.Count!=3||w.HasHint)throw new Exception("Xiangqi undo statistics/continuation mismatch");
   w.ToggleReview();byte[] initial=w.ReviewXiangqi(),expected=XiangqiModel.StartBoard();for(int i=0;i<90;i++)if(initial[i]!=expected[i])throw new Exception("Xiangqi replay initial board");
   w.ReviewJump(1);if(w.ReviewXiangqi()[54]!=0||w.ReviewXiangqi()[45]!=7)throw new Exception("Xiangqi replay first move");
   if(!String.IsNullOrEmpty(screenshot)){using(Bitmap b=new Bitmap(w.Width,w.Height)){w.DrawToBitmap(b,new Rectangle(0,0,w.Width,w.Height));b.Save(screenshot+".review.png",System.Drawing.Imaging.ImageFormat.Png);}}
   w.ReviewJump(2);for(int i=0;i<90;i++)if(w.ReviewXiangqi()[i]!=live[i])throw new Exception("Xiangqi replay final board");
   w.ToggleReview();if(w.xm.Count!=2||w.stats.Text!=xiangqiStats)throw new Exception("Review altered live game/statistics");
   w.RequestHint();w.suspended=true;w.link.Send("STOP");wait(()=>!w.busy);if(w.xm.Count!=2)throw new Exception("Cancelled hint changed game");
   // Legal opening: central cannon, advance/capture central pawn to expose
   // one screen against the black king. The advisor then blocks the check.
   w.assist.Checked=false;w.human=1;w.colour.SelectedIndex=1;
   w.replay=new Queue<Point>(new Point[]{new Point(64,67),new Point(27,36),new Point(58,49),new Point(36,45),new Point(49,40),new Point(29,38),new Point(40,31)});
   w.loading=true;w.suspended=true;w.SendBusy("NEW");wait(()=>!w.busy&&w.xm.Count==7);
   if(w.xm.Checked!=1||!w.DisplayedCheck||w.CheckedKingSquare!=4||w.BoardResultText!=null)throw new Exception("FPGA protocol check notice/king mapping");
   if(!String.IsNullOrEmpty(screenshot)){using(Bitmap b=new Bitmap(w.Width,w.Height)){w.DrawToBitmap(b,new Rectangle(0,0,w.Width,w.Height));b.Save(screenshot+".check.png",System.Drawing.Imaging.ImageFormat.Png);}}
   w.ToggleReview();w.ReviewJump(6);if(w.DisplayedCheck)throw new Exception("Check leaked into earlier replay");w.ReviewJump(7);if(!w.DisplayedCheck||w.CheckedKingSquare!=4)throw new Exception("Check replay missing");w.ToggleReview();
   w.suspended=true;w.SendBusy("PLAY 3 13");wait(()=>!w.busy&&w.xm.Count==8);if(w.DisplayedCheck)throw new Exception("Check notice remained after legal evasion");
   w.undo.PerformClick();wait(()=>!w.busy&&w.xm.Count==7);if(!w.DisplayedCheck||w.checkHistory.Count!=8)throw new Exception("Undo did not restore check");
   w.xm.Outcome=1;if(w.DisplayedCheck)throw new Exception("Check notice overlaps terminal result");w.xm.Outcome=0;w.colour.SelectedIndex=0;
   w.TestFenLoading(wait);
   w.assist.Checked=false;w.game.SelectedIndex=0;w.SelectGame();wait(()=>w.active==1&&!w.busy);if(w.gm.Count!=0||w.HasHint)throw new Exception("Game reset");
   w.colour.SelectedIndex=1;w.NewGame();wait(()=>!w.busy&&w.gm.Count==1);w.SetHover(111);
   if(!String.IsNullOrEmpty(screenshot)){using(Bitmap b=new Bitmap(w.Width,w.Height)){w.DrawToBitmap(b,new Rectangle(0,0,w.Width,w.Height));b.Save(screenshot+".gomoku-white.png",System.Drawing.Imaging.ImageFormat.Png);}}if(w.gm.Board[6,7]!=0||w.gm.Count!=1)throw new Exception("White preview changed board");
   w.colour.SelectedIndex=0;w.NewGame();wait(()=>!w.busy&&w.gm.Count==0);if(w.stats.Text!=NoSearchStats||w.statsHistory.Count!=1)throw new Exception("New game kept old statistics");
   // Feed an ordinary legal winning game through the real host protocol.
   w.replay=new Queue<Point>(new Point[]{new Point(2,7),new Point(1,7),new Point(3,7),new Point(0,0),new Point(4,7),new Point(2,0),new Point(5,7),new Point(4,0),new Point(6,7)});
   w.loading=true;w.suspended=true;w.SendBusy("NEW");wait(()=>!w.busy&&w.gm.Count==9);if(w.gm.Winner!=1||w.BoardResultText!="获胜"||w.BoardResultColor!=Color.Red)throw new Exception("Win overlay mapping");
   w.ToggleReview();w.ReviewJump(8);if(w.BoardResultText!=null)throw new Exception("Win overlay leaked into earlier review position");w.ReviewJump(9);if(w.BoardResultText!="获胜")throw new Exception("Final review overlay missing");w.ToggleReview();
   if(!String.IsNullOrEmpty(screenshot)){using(Bitmap b=new Bitmap(w.Width,w.Height)){w.DrawToBitmap(b,new Rectangle(0,0,w.Width,w.Height));b.Save(screenshot+".victory.png",System.Drawing.Imaging.ImageFormat.Png);}}
   w.human=1;if(w.BoardResultText!="落败"||w.BoardResultColor!=Color.Black)throw new Exception("Defeat overlay mapping");
   if(!String.IsNullOrEmpty(screenshot)){using(Bitmap b=new Bitmap(w.Width,w.Height)){w.DrawToBitmap(b,new Rectangle(0,0,w.Width,w.Height));b.Save(screenshot+".defeat.png",System.Drawing.Imaging.ImageFormat.Png);}}
   w.human=0;w.undo.PerformClick();wait(()=>!w.busy&&w.gm.Count==8);if(w.BoardResultText!=null||w.stats.Text!=NoSearchStats)throw new Exception("Undo did not clear result overlay/statistics");
   // Both game protocols encode winners as human+1, despite different Side encodings.
   w.active=2;for(int who=0;who<2;who++){w.human=who;for(int result=1;result<=2;result++){w.xm.Outcome=result;bool won=result==who+1;if(w.BoardResultText!=(won?"获胜":"落败")||w.BoardResultColor!=(won?Color.Red:Color.Black))throw new Exception("Xiangqi result perspective");}}
   w.xm.Outcome=3;if(w.BoardResultText!=null)throw new Exception("Draw shown as a defeat");w.active=1;w.human=0;
   if(!String.IsNullOrEmpty(screenshot)){using(Bitmap b=new Bitmap(w.Width,w.Height)){w.DrawToBitmap(b,new Rectangle(0,0,w.Width,w.Height));b.Save(screenshot,System.Drawing.Imaging.ImageFormat.Png);}}
   Size oldSize=w.ClientSize;Rectangle oldBounds=w.Bounds;
   foreach(Size size in new Size[]{new Size(1600,900),new Size(1280,1024)}){
    w.ClientSize=size;Application.DoEvents();
    PointF origin=w.BoardOrigin;Point mapped=w.BoardPoint((int)Math.Round(origin.X+300*w.BoardScale),(int)Math.Round(origin.Y+300*w.BoardScale));
    if(Math.Abs(mapped.X-300)>1||Math.Abs(mapped.Y-300)>1)throw new Exception("Scaled board input mapping");
    foreach(Control c in w.Controls)if(c.Right>w.ClientSize.Width+2||c.Bottom>w.ClientSize.Height+2)throw new Exception("Responsive layout outside window");
   }
   if(!String.IsNullOrEmpty(screenshot)){using(Bitmap b=new Bitmap(w.Width,w.Height)){w.DrawToBitmap(b,new Rectangle(0,0,w.Width,w.Height));b.Save(screenshot+".resized.png",System.Drawing.Imaging.ImageFormat.Png);}}
   w.Bounds=oldBounds;w.ClientSize=oldSize;Application.DoEvents();oldBounds=w.Bounds;
   w.ToggleFullscreen();Application.DoEvents();if(w.FormBorderStyle!=FormBorderStyle.None||w.Bounds!=Screen.FromControl(w).Bounds)throw new Exception("Fullscreen bounds");
   w.ToggleFullscreen();Application.DoEvents();if(w.FormBorderStyle!=FormBorderStyle.Sizable||w.Bounds!=oldBounds)throw new Exception("Fullscreen restore");
   w.Close();
  }
 }
}
