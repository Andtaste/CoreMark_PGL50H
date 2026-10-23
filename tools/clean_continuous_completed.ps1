param([string[]]$Names=@('control','side_select','mem_capture','btb128','btb_fold','branch_equal'), [switch]$DryRun)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$resultsRoot=(Resolve-Path (Join-Path $projectRoot 'simulation/results')).Path
$recordRoot=Join-Path $resultsRoot 'autonomous_20261022'
$removed=[Collections.Generic.List[object]]::new()
foreach($name in $Names) {
 if($name -notmatch '^[a-z0-9_]+$' -or $name -eq 'original_board'){throw "Invalid trial name: $name"}
 $sim=Join-Path $resultsRoot ('load_bp_dual_boundary_auto_'+$name)
 $physical=Join-Path $recordRoot $name
 $performanceResult=Join-Path $sim 'performance/result.json'
 $derivationPath=Join-Path $physical 'derivation.json'
 if(!(Test-Path -LiteralPath $performanceResult) -and (Test-Path -LiteralPath $derivationPath)) {
  $derivation=Get-Content -LiteralPath $derivationPath -Raw | ConvertFrom-Json
  if($derivation.identical_inputs -and $derivation.parent_trial -match '^[a-z0-9_]+$') {
   $performanceResult=Join-Path $resultsRoot ('load_bp_dual_boundary_auto_'+$derivation.parent_trial+'/performance/result.json')
  }
 }
 # Only explicitly completed rounds may be passed. Never touch hardware projects,
 # original_board, software inputs, RTL, benches, JSON results, or textual reports.
 if(!(Test-Path -LiteralPath $performanceResult)){throw "No completed performance result: $name"}
 $nativeLog=Join-Path $physical 'native_build.log'
 if((Test-Path -LiteralPath $nativeLog) -and !((Get-Content -LiteralPath $nativeLog -Raw).Contains('Process "Report Timing" done.'))) {throw "Physical trial not completed: $name"}
 $targets=[Collections.Generic.List[object]]::new()
 foreach($root in @($sim,$physical)) {
  if(!(Test-Path -LiteralPath $root)){continue}
  $resolvedRoot=(Resolve-Path -LiteralPath $root).Path
  if(!$resolvedRoot.StartsWith($resultsRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Target outside results'}
  foreach($dir in Get-ChildItem -LiteralPath $resolvedRoot -Directory -Recurse | Where-Object Name -eq 'obj') {
   $targets.Add($dir)
  }
  foreach($file in Get-ChildItem -LiteralPath $resolvedRoot -File -Recurse | Where-Object { $_.Extension -in @('.vvp','.trace','.vcd','.fst') -and $_.FullName -notmatch '[\\/]obj[\\/]' }) {
   $targets.Add($file)
  }
  if($root -eq $physical -and $name -ne 'btb_fold') {
   foreach($stage in @('compile','synthesize','device_map','place_route','report_timing','constraint_check')) {
    $stagePath=Join-Path $resolvedRoot $stage
    if(Test-Path -LiteralPath $stagePath) {
     foreach($file in Get-ChildItem -LiteralPath $stagePath -File -Recurse | Where-Object { $_.Extension -in @('.adf','.db','.vm','.netlist') }) {$targets.Add($file)}
    }
   }
  }
  foreach($target in $targets | Where-Object { $_.FullName.StartsWith($resolvedRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) }) {
   $resolved=(Resolve-Path -LiteralPath $target.FullName).Path
   if(!$resolved.StartsWith($resolvedRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw "Unsafe target: $resolved"}
   $bytes=if($target.PSIsContainer){(Get-ChildItem -LiteralPath $resolved -File -Recurse | Measure-Object Length -Sum).Sum}else{$target.Length}
   $removed.Add([pscustomobject]@{path=$resolved;bytes=$bytes})
   if(!$DryRun){Remove-Item -LiteralPath $resolved -Recurse -Force}
  }
 }
}
$total=($removed | Measure-Object bytes -Sum).Sum
$receipt=[ordered]@{dry_run=[bool]$DryRun;names=$Names;removed_bytes=$total;removed=$removed;preserved='Original backup, accepted hardware project, RTL/IP/images, benches, result JSON, logs and textual timing/resource reports'}
$receiptPath=Join-Path $recordRoot ('cleanup_'+(Get-Date -Format 'yyyyMMdd_HHmmss')+$(if($DryRun){'_preview'}else{''})+'.json')
$receipt | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $receiptPath
Write-Output ("{0} targets, {1:N1} MiB; receipt {2}" -f $removed.Count,($total/1MB),$receiptPath)
