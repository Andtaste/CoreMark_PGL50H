$ErrorActionPreference='Stop'
$workspace=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$receiptDir=Join-Path $workspace 'new_core\docs\fpga_cleanup_execution_20261022'
$preparedPath=Join-Path $receiptDir 'prepared.json'
$receiptPath=Join-Path $receiptDir 'execution.json'
if(Test-Path -LiteralPath $receiptPath){throw 'Execution already recorded; do not overwrite'}
$prepared=Get-Content -LiteralPath $preparedPath -Raw | ConvertFrom-Json
if($prepared.status -ne 'PREFLIGHT_PASS' -or [IO.Path]::GetFullPath($prepared.root) -ne $workspace){throw 'Wrong preflight/root'}
$planPath=Join-Path $workspace 'new_core\docs\fpga_cleanup_audit_20261022\candidate_files.json'
if((Get-FileHash -LiteralPath $planPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $prepared.candidate_plan_sha256){throw 'Authorized candidate list changed'}
function Assert-NoBuild {
 $running=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^(pds|vvp|iverilog|verilator|make|gmake|riscv).*'})
 if($running.Count -gt 0){throw ('Build/simulation process active: '+(($running | ForEach-Object {$_.Name+':'+$_.ProcessId}) -join ', '))}
}
Assert-NoBuild
$targets=[Collections.Generic.List[object]]::new()
$skipped=[Collections.Generic.List[object]]::new()
$deleted=[Collections.Generic.List[object]]::new()
$failed=[Collections.Generic.List[object]]::new()
$seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach($entry in $prepared.approved){
 $computed=[IO.Path]::GetFullPath((Join-Path $workspace $entry.path))
 if(-not $computed.StartsWith($workspace+'\',[StringComparison]::OrdinalIgnoreCase) -or $computed -ne $entry.absolute_path){throw 'Target escaped explicit workspace'}
 if(-not $seen.Add($computed)){throw 'Duplicate target'}
 if(-not (Test-Path -LiteralPath $computed -PathType Leaf)){$skipped.Add([ordered]@{path=$entry.path;reason='Already absent before execution'});continue}
 $full=(Resolve-Path -LiteralPath $computed).Path
 if($full -ne $computed -or -not $full.StartsWith($workspace+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Resolved target escaped workspace'}
 $item=Get-Item -LiteralPath $full -Force
 $cursor=$item
 while($null -ne $cursor -and $cursor.FullName.Length -ge $workspace.Length){
  if($cursor.Attributes -band [IO.FileAttributes]::ReparsePoint){throw ('Reparse point: '+$cursor.FullName)}
  if($cursor.FullName -eq $workspace){break}
  if($cursor.PSIsContainer){$cursor=$cursor.Parent}else{$cursor=$cursor.Directory}
 }
 if($item.PSIsContainer -or $item.Length -ne [long]$entry.bytes -or $item.LastWriteTimeUtc.Ticks -ne [long]$entry.last_write_utc_ticks){$skipped.Add([ordered]@{path=$entry.path;reason='Metadata changed since audit/preflight'});continue}
 $targets.Add($entry)
}
# Every exact target has been resolved and checked before any deletion.
foreach($name in $prepared.critical_paths){
 $path=Join-Path $workspace $name
 $expected=$prepared.protected_sha256.PSObject.Properties[$name].Value
 if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected){throw ('Critical baseline changed: '+$name)}
}
Assert-NoBuild
$counter=0
foreach($entry in $targets){
 if(($counter % 100) -eq 0){Assert-NoBuild}
 $counter++
 try {
  $item=Get-Item -LiteralPath $entry.absolute_path -Force
  if($item.Length -ne [long]$entry.bytes -or $item.LastWriteTimeUtc.Ticks -ne [long]$entry.last_write_utc_ticks){$skipped.Add([ordered]@{path=$entry.path;reason='Changed immediately before deletion'});continue}
  # Literal single-file deletion only; no recursive directory removal.
  Remove-Item -LiteralPath $entry.absolute_path -Force -ErrorAction Stop
  if(Test-Path -LiteralPath $entry.absolute_path){throw 'File still exists after Remove-Item'}
  $deleted.Add([ordered]@{path=$entry.path;bytes=[long]$entry.bytes;category=$entry.category})
 } catch {$failed.Add([ordered]@{path=$entry.path;reason=$_.Exception.Message})}
}
$removedBytes=[long]0
foreach($entry in $deleted){$removedBytes+=$entry.bytes}
$result=[ordered]@{status=$(if($failed.Count -eq 0 -and $skipped.Count -eq 0 -and $prepared.skipped.Count -eq 0){'CLEANUP_COMPLETED'}else{'CLEANUP_COMPLETED_WITH_SKIPS'});scope='Explicit authorized cache files only; native single-file PowerShell deletion; no recursive directory deletion';root=$workspace;candidate_plan_sha256=$prepared.candidate_plan_sha256;prepared_sha256=(Get-FileHash -LiteralPath $preparedPath -Algorithm SHA256).Hash.ToLowerInvariant();deleted_files=$deleted.Count;deleted_logical_bytes=$removedBytes;preflight_skipped=$prepared.skipped;runtime_skipped=$skipped;failed=$failed;deleted=$deleted}
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
Write-Output "CLEANUP: $($deleted.Count) files, $removedBytes logical bytes; preflight skipped $($prepared.skipped.Count), runtime skipped $($skipped.Count), failed $($failed.Count)"
