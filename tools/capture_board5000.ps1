param([Parameter(Mandatory=$true)][string]$Port,[int]$Seconds=60,[string]$Python='',[int]$CpuHz=83000000)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
if(!$Python){$Python=(Get-Command python -ErrorAction SilentlyContinue).Source}
if(!$Python){$Python=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'}
$logDirectory=Join-Path $projectRoot 'logs/board5000'
New-Item -ItemType Directory -Force $logDirectory | Out-Null
$logPath=Join-Path $logDirectory ((Get-Date -Format 'yyyyMMdd_HHmmss')+'.uart.txt')
$serial=[System.IO.Ports.SerialPort]::new($Port,115200,[System.IO.Ports.Parity]::None,8,[System.IO.Ports.StopBits]::One)
$serial.Handshake=[System.IO.Ports.Handshake]::None
$serial.DtrEnable=$false
$serial.RtsEnable=$false
$serial.ReadTimeout=200
$writer=[System.IO.StreamWriter]::new($logPath,$false,[System.Text.UTF8Encoding]::new($false))
$text=[System.Text.StringBuilder]::new()
try {
 $serial.Open()
 Write-Host "Listening on $Port at115200/8N1. Press board KEY1 to restart CoreMark5000."
 $deadline=(Get-Date).AddSeconds($Seconds)
 while((Get-Date) -lt $deadline){
  $chunk=$serial.ReadExisting()
  if($chunk){$writer.Write($chunk);$writer.Flush();[void]$text.Append($chunk);Write-Host -NoNewline $chunk}
  if($text.ToString().Contains('IPC/CPI use retired instructions and cycles from the same stats window.')){break}
  Start-Sleep -Milliseconds 30
 }
} finally {$writer.Dispose();if($serial.IsOpen){$serial.Close()};$serial.Dispose()}
Write-Host "UART saved: $logPath"
& $Python -X utf8 (Join-Path $PSScriptRoot 'verify_board5000_uart.py') $logPath --cpu-hz $CpuHz
if($LASTEXITCODE -ne 0){throw 'UART transcript incomplete or checks failed; inspect the saved log.'}
