$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$out=Join-Path $root 'output/board_games'
$x=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'xiangqi_client.cs'))
$x=$x.Substring(0,$x.IndexOf('public sealed class XiangqiWindow'))
$g=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'play_gomoku.ps1'))
$start=$g.IndexOf('public sealed class GomokuModel')
$g=$g.Substring($start,$g.IndexOf('public sealed class GomokuLink')-$start)
$client=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'board_games_client.cs'))
$entry=@'
public static class DesktopEntry {
 [STAThread] public static void Main(string[] args) {
  string engine=Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"../../sw/build/board_games/board_games_host.exe"));
  bool local=args.Length>0&&args[0]=="--local";
  BoardGamesWindow.Start(local?null:args.Length>0?args[0]:"COM13",engine,local);
 }
}
'@
[IO.Directory]::CreateDirectory($out) | Out-Null
$source=Join-Path $out 'desktop_client.cs'
[IO.File]::WriteAllText($source,$x+$g+$client+$entry,[Text.Encoding]::UTF8)
$compiler=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
& $compiler /nologo /target:winexe /optimize+ /reference:System.Windows.Forms.dll /reference:System.Drawing.dll "/out:$out/board_games_desktop.exe" $source
if($LASTEXITCODE -ne 0){throw 'Desktop compilation failed'}
Write-Output "Built $out/board_games_desktop.exe"
