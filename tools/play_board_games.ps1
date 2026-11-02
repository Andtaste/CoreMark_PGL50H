param([string]$Port,[switch]$Local,[switch]$ListPorts,[switch]$SelfTest,[switch]$UiTest,[string]$Preview)
$ErrorActionPreference='Stop'
if (-not ('System.IO.Ports.SerialPort' -as [type])) { Add-Type -AssemblyName System.IO.Ports }
if ($ListPorts) { [System.IO.Ports.SerialPort]::GetPortNames() | Sort-Object; exit 0 }
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$root=Split-Path $PSScriptRoot -Parent
$x=[System.IO.File]::ReadAllText((Join-Path $PSScriptRoot 'xiangqi_client.cs'))
$x=$x.Substring(0,$x.IndexOf('public sealed class XiangqiWindow'))
$g=[System.IO.File]::ReadAllText((Join-Path $PSScriptRoot 'play_gomoku.ps1'))
$start=$g.IndexOf('public sealed class GomokuModel')
$g=$g.Substring($start,$g.IndexOf('public sealed class GomokuLink')-$start)
$client=[System.IO.File]::ReadAllText((Join-Path $PSScriptRoot 'board_games_client.cs'))
Add-Type -TypeDefinition ($x+$g+$client) -ReferencedAssemblies System.Windows.Forms,System.Drawing
if ($SelfTest) { [XiangqiModel]::Test(); [GomokuModel]::Test(); [GomokuReview]::Test(); 'PASS: reused chess models/replay'; exit 0 }
$exe=Join-Path $root 'sw/build/board_games/board_games_host.exe'
if ($UiTest) {
 [BoardGamesWindow]::TestHost($exe,$Preview)
 $resultDir=Join-Path $root 'simulation/results/board_games'
 [System.IO.Directory]::CreateDirectory($resultDir) | Out-Null
 $hashes=@{}
 foreach($name in @('tools/play_board_games.ps1','tools/board_games_client.cs','tools/xiangqi_client.cs','tools/play_gomoku.ps1','sw/build/board_games/board_games_host.exe')) {
  $hashes[$name]=(Get-FileHash -LiteralPath (Join-Path $root $name) -Algorithm SHA256).Hash.ToLowerInvariant()
 }
 @{status='UNIFIED_REAL_FORM_HOST_ENGINE_PASS';input_sha256=$hashes} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $resultDir 'ui_result.json') -Encoding utf8
 $pass='PASS: unified form/host transport,game selection,both mouse boards,AI response,replay,switching,undo statistics snapshots,victory/defeat overlays,check/evasion/undo/review notices,FEN red/black import,hints,save/reload,undo,review,and rejected-position preservation'
 [System.IO.File]::WriteAllText((Join-Path $resultDir 'ui.log'),$pass+[Environment]::NewLine,[System.Text.Encoding]::UTF8)
 $pass; exit 0
}
if (-not ($Port -or $Local)) { throw 'Use -Port COM13 or -Local (explicit HOST TEST).' }
[BoardGamesWindow]::Start($Port,$exe,[bool]$Local)
