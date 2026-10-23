param([switch]$DryRun)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$resultsRoot=(Resolve-Path (Join-Path $projectRoot 'simulation/results')).Path
$records=[Collections.Generic.List[object]]::new()
$clockLabels=[Collections.Generic.HashSet[string]]::new()
$roots=[Collections.Generic.List[string]]::new()
foreach($trial in Get-ChildItem -LiteralPath $resultsRoot -Directory -Filter 'continuous_clock*_20261022') {
 $label=$trial.Name -replace '^continuous_clock','' -replace '_20261022$',''
 if($label -notmatch '^\d+(p\d+)?(_[a-z0-9]+)*$'){continue}
 $checkLabel=$label -replace '_p\d+r\d+$',''
 $evaluation=Join-Path $trial.FullName 'evaluation.json'
 if(!(Test-Path -LiteralPath $evaluation)){continue}
 $result=Get-Content -LiteralPath $evaluation -Raw | ConvertFrom-Json
 if($result.status -notin @('FAIL','INVALID_CONFIGURATION')){continue}
 $logText=Get-Content -LiteralPath (Join-Path $trial.FullName 'native_build.log') -Raw
 if($result.status -eq 'FAIL' -and !$logText.Contains('Process "Report Timing" done.')){continue}
 if($result.status -eq 'INVALID_CONFIGURATION' -and !($logText.Contains('Flow-0186') -and $logText.Contains('Program Error Out.'))){continue}
 $roots.Add($trial.FullName);[void]$clockLabels.Add($checkLabel)
}
foreach($label in $clockLabels) {
 $checks=Join-Path $resultsRoot ("continuous_clock{0}_checks" -f $label)
 $io=Join-Path $resultsRoot ("continuous_clock{0}_io" -f $label)
 if((Test-Path -LiteralPath (Join-Path $checks 'result.json')) -and (Test-Path -LiteralPath (Join-Path $checks 'metadata_result.json'))){$roots.Add($checks)}
 if(Test-Path -LiteralPath (Join-Path $io 'result.json')){$roots.Add($io)}
}
foreach($root in $roots) {
 $resolvedRoot=(Resolve-Path -LiteralPath $root).Path
 if(!$resolvedRoot.StartsWith($resultsRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Outside result scope'}
 $targets=[Collections.Generic.List[object]]::new()
 foreach($dir in Get-ChildItem -LiteralPath $resolvedRoot -Directory -Recurse | Where-Object Name -eq 'obj'){$targets.Add($dir)}
 foreach($file in Get-ChildItem -LiteralPath $resolvedRoot -File -Recurse | Where-Object { $_.Extension -in @('.vvp','.trace','.vcd','.fst') -and $_.FullName -notmatch '[\\/]obj[\\/]' }){$targets.Add($file)}
 foreach($stage in @('compile','synthesize','device_map','place_route','report_timing','constraint_check')) {
  $stagePath=Join-Path $resolvedRoot $stage
  if(Test-Path -LiteralPath $stagePath){foreach($file in Get-ChildItem -LiteralPath $stagePath -File -Recurse | Where-Object {$_.Extension -in @('.adf','.db','.vm','.netlist')}){$targets.Add($file)}}
 }
 foreach($target in $targets) {
  $resolved=(Resolve-Path -LiteralPath $target.FullName).Path
  if(!$resolved.StartsWith($resolvedRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw "Unsafe target: $resolved"}
  $bytes=if($target.PSIsContainer){(Get-ChildItem -LiteralPath $resolved -File -Recurse | Measure-Object Length -Sum).Sum}else{$target.Length}
  $records.Add([pscustomobject]@{path=$resolved;bytes=$bytes})
  if(!$DryRun){Remove-Item -LiteralPath $resolved -Recurse -Force}
 }
}
$total=($records | Measure-Object bytes -Sum).Sum
$receipt=Join-Path $resultsRoot ('autonomous_20261022/clock_cleanup_'+(Get-Date -Format 'yyyyMMdd_HHmmss')+$(if($DryRun){'_preview'}else{''})+'.json')
[ordered]@{dry_run=[bool]$DryRun;roots=$roots;removed_bytes=$total;removed=$records;preserved='Input RTL/IP/firmware, result/manifest JSON, textual reports, test benches, logs; no accepted hardware project touched'} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $receipt
Write-Output ("{0} targets, {1:N1} MiB; receipt {2}" -f $records.Count,($total/1MB),$receipt)
