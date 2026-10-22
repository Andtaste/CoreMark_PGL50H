$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskResultRoot = [IO.Path]::GetFullPath((Join-Path $taskRoot 'simulation\results'))
$taskInventory = Get-Content -LiteralPath (Join-Path $taskRoot 'simulation\cleanup_inventory.json') -Raw | ConvertFrom-Json
if ([IO.Path]::GetFullPath($taskInventory.root) -ne $taskRoot) { throw 'Inventory belongs to another workspace.' }
$taskTargets = @()
$taskSkipped = @()
foreach ($taskEntry in $taskInventory.obj_bytes.PSObject.Properties) {
    $taskAbsolute = [IO.Path]::GetFullPath((Join-Path $taskRoot $taskEntry.Name))
    if (!$taskAbsolute.StartsWith($taskResultRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw "Outside simulation results: $taskAbsolute" }
    if ([IO.Path]::GetFileName($taskAbsolute) -ne 'obj') { throw "Not an obj directory: $taskAbsolute" }
    if ($taskEntry.Name -match 'load_bp_dual_lsu_') { $taskSkipped += $taskEntry.Name; continue }
    if (!(Test-Path -LiteralPath $taskAbsolute)) { continue }
    $taskCursor = Get-Item -LiteralPath $taskAbsolute
    while ($taskCursor.FullName.Length -ge $taskResultRoot.Length) {
        if ($taskCursor.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse point: $($taskCursor.FullName)" }
        $taskCursor = $taskCursor.Parent
    }
    if (Get-ChildItem -LiteralPath $taskAbsolute -Force -Recurse | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }) { throw "Reparse point inside: $taskAbsolute" }
    $taskTargets += [PSCustomObject]@{ path = $taskAbsolute; bytes = [long]$taskEntry.Value }
}
# Every resolved target above was checked before the first recursive deletion.
foreach ($taskTarget in $taskTargets) {
    Remove-Item -LiteralPath $taskTarget.path -Recurse -Force
    if (Test-Path -LiteralPath $taskTarget.path) { throw "Cache deletion incomplete: $($taskTarget.path)" }
}
$taskReport = [ordered]@{
    date = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    root = $taskRoot
    removed_directories = $taskTargets.Count
    reclaimed_bytes = [long](($taskTargets | Measure-Object -Property bytes -Sum).Sum)
    scope = 'Historical simulation/results/**/obj only. Preserved all load_bp_dual_lsu_* directories, RTL, images, traces, logs, JSON results, PDS outputs and immutable docs archives.'
    skipped = $taskSkipped
    removed = $taskTargets
}
$taskReport | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskRoot 'simulation\cleanup_result.json') -Encoding utf8
[PSCustomObject]@{ removed_directories=$taskTargets.Count; reclaimed_GiB=[Math]::Round($taskReport.reclaimed_bytes/1GB,3); skipped=$taskSkipped.Count } | ConvertTo-Json
