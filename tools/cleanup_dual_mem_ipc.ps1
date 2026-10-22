$ErrorActionPreference='Stop'
$workspace=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$roots=@('memprobe','storeack','storemmio','storeprefix') | ForEach-Object { Join-Path $workspace "simulation\results\load_bp_dual_boundary_$_" }
$targets=@()
foreach($root in $roots){
 $resolved=(Resolve-Path -LiteralPath $root).Path
 if(-not $resolved.StartsWith($workspace+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Root outside workspace'}
 if((Get-Item -LiteralPath $resolved).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse root'}
 foreach($phase in @('performance','validation')){
  $path=Join-Path $resolved "$phase\obj"
  if(Test-Path -LiteralPath $path){
   $full=(Resolve-Path -LiteralPath $path).Path
   if(-not $full.StartsWith($resolved+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Target escaped root'}
   $items=@(Get-Item -LiteralPath $full)+@(Get-ChildItem -LiteralPath $full -Recurse -Force)
   if($items | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }){throw 'Reparse in cache'}
   $bytes=($items | Where-Object {-not $_.PSIsContainer} | Measure-Object -Property Length -Sum).Sum
   $targets+=@([ordered]@{path=$full;bytes=$bytes})
  }
 }
}
$totalBytes=[long]0
foreach($target in $targets){$totalBytes+=$target['bytes'];Remove-Item -LiteralPath $target.path -Recurse -Force}
[ordered]@{status='PASS';scope='Only completed isolated Verilator obj caches; sources/images/logs/STA preserved';removed=$targets;bytes=$totalBytes} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $workspace 'simulation\cleanup_dual_mem_ipc_result.json') -Encoding UTF8
$targets | Format-Table
