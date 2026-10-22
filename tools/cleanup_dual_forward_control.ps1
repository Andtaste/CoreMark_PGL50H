$ErrorActionPreference='Stop'
$workspace=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$targets=@()
foreach($name in @('headmux','pcselect')){
 $root=(Resolve-Path -LiteralPath (Join-Path $workspace "simulation\results\load_bp_dual_boundary_$name")).Path
 if(-not $root.StartsWith($workspace+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Root outside workspace'}
 if((Get-Item -LiteralPath $root).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse root'}
 foreach($phase in @('performance','validation')){
  $p=Join-Path $root "$phase\obj"
  if(Test-Path -LiteralPath $p){
   $full=(Resolve-Path -LiteralPath $p).Path
   if(-not $full.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Cache escaped root'}
   $items=@(Get-Item -LiteralPath $full)+@(Get-ChildItem -LiteralPath $full -Recurse -Force)
   if($items | Where-Object {$_.Attributes -band [IO.FileAttributes]::ReparsePoint}){throw 'Reparse in cache'}
   $targets+=@([ordered]@{path=$full;bytes=($items | Where-Object {-not $_.PSIsContainer} | Measure-Object -Property Length -Sum).Sum})
  }
 }
}
$totalBytes=[long]0
foreach($target in $targets){$totalBytes+=$target['bytes'];Remove-Item -LiteralPath $target.path -Recurse -Force}
[ordered]@{status='PASS';scope='Completed isolated Verilator obj caches only; sources/images/logs/STA retained';removed=$targets;bytes=$totalBytes} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $workspace 'simulation\cleanup_dual_forward_control_result.json') -Encoding UTF8
Write-Output "Removed $($targets.Count) caches, $totalBytes bytes"
