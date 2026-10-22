$ErrorActionPreference='Stop'
$taskRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$resultsRoot=Join-Path $taskRoot 'simulation\results'
$archiveRoot=Join-Path $taskRoot 'docs\dual_resource_trials'
$prepared=Get-Content -LiteralPath (Join-Path $archiveRoot 'archive_verification.json') -Raw | ConvertFrom-Json
if($prepared.status -ne 'PASS'){throw 'Snapshots/evidence not verified'}
$acceptedPath=Join-Path $taskRoot 'docs\accepted_dual_baseline.json'
$acceptedBefore=(Get-FileHash -LiteralPath $acceptedPath -Algorithm SHA256).Hash.ToLowerInvariant()
if($acceptedBefore -ne $prepared.accepted_descriptor_sha256){throw 'Accepted baseline changed'}
$trialNames=@('resourceside','resourcequeue','resourceboth','resourcecompare')
$targets=[Collections.Generic.List[object]]::new()
function Add-CheckedCache([string]$trialRoot,[string]$relative){
 $candidate=[IO.Path]::GetFullPath((Join-Path $trialRoot $relative))
 if(-not $candidate.StartsWith($trialRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw "Outside trial: $candidate"}
 if(-not(Test-Path -LiteralPath $candidate)){return}
 $item=Get-Item -LiteralPath $candidate -Force
 if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw "Reparse target: $candidate"}
 if(-not $item.PSIsContainer){
  if($item.Name -ne 'rtr.db'){throw "Expected cache directory: $candidate"}
  $targets.Add([pscustomobject]@{path=$candidate;root=$trialRoot;files=1;bytes=[long]$item.Length;directory=$false})
  return
 }
 $children=@(Get-ChildItem -LiteralPath $candidate -Recurse -Force)
 if(@($children | Where-Object {($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0}).Count){throw "Reparse child: $candidate"}
 $files=@($children | Where-Object {-not $_.PSIsContainer})
 $bytes=($files | Measure-Object -Property Length -Sum).Sum
 $targets.Add([pscustomobject]@{path=$candidate;root=$trialRoot;files=$files.Count;bytes=[long]$bytes;directory=$true})
}
foreach($trialName in $trialNames){
 $trialRoot=[IO.Path]::GetFullPath((Join-Path $resultsRoot ('load_bp_dual_boundary_next_'+$trialName)))
 if(-not $trialRoot.StartsWith($resultsRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Trial escaped results'}
 if(@(Get-ChildItem -LiteralPath $trialRoot -Recurse -Force | Where-Object {($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0}).Count){throw "Reparse item in trial: $trialRoot"}
 foreach($relative in @('performance\obj','validation\obj','pds\compile','pds\report_timing\rtr.db','next_paths\compile','next_paths\report_timing\rtr.db')){Add-CheckedCache $trialRoot $relative}
 foreach($file in @(Get-ChildItem -LiteralPath $trialRoot -Recurse -File -Filter '*.vvp')){
  $absolute=[IO.Path]::GetFullPath($file.FullName)
  if(($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw "Reparse VVP: $absolute"}
  if(-not $absolute.StartsWith($trialRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'VVP escaped trial'}
  $targets.Add([pscustomobject]@{path=$absolute;root=$trialRoot;files=1;bytes=[long]$file.Length;directory=$false})
 }
}
$removed=[Collections.Generic.List[object]]::new()
foreach($target in $targets){
 $resolved=(Resolve-Path -LiteralPath $target.path).ProviderPath
 if($resolved -ne $target.path -or -not $resolved.StartsWith($target.root+'\',[StringComparison]::OrdinalIgnoreCase)){throw "Resolved target escaped: $resolved"}
 if($target.directory){Remove-Item -LiteralPath $resolved -Recurse -Force}else{Remove-Item -LiteralPath $resolved -Force}
 $removed.Add($target)
}
$acceptedAfter=(Get-FileHash -LiteralPath $acceptedPath -Algorithm SHA256).Hash.ToLowerInvariant()
if($acceptedAfter -ne $acceptedBefore){throw 'Accepted descriptor changed during cleanup'}
$receipt=[ordered]@{status='PASS';scope='Only this task new trial obj/VVP/PDS compile/STA-query DB caches; verified routed snapshots and evidence retained';bytes=[long](($removed | Measure-Object -Property bytes -Sum).Sum);files=[long](($removed | Measure-Object -Property files -Sum).Sum);accepted_descriptor_sha256=$acceptedAfter;removed=@($removed)}
$receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $taskRoot 'simulation\cleanup_dual_resource_trials_result.json') -Encoding utf8
Write-Output ('CLEANED '+$receipt.files+' files / '+$receipt.bytes+' bytes; accepted baseline unchanged')
