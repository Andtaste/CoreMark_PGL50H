$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskResultRoot = [IO.Path]::GetFullPath((Join-Path $taskRoot 'simulation\results'))
$taskTargets = @()
foreach ($taskVariant in @('shared', 'ports', 'forward', 'pair')) {
    foreach ($taskPhase in @('performance', 'validation')) {
        $taskPhasePath = Join-Path $taskResultRoot "load_bp_dual_lsu_$taskVariant\$taskPhase"
        $taskResult = Get-Content -LiteralPath (Join-Path $taskPhasePath 'result.json') -Raw | ConvertFrom-Json
        if ($taskResult.status -ne 'PASS') { throw "Unfinished simulation: $taskPhasePath" }
        $taskAbsolute = [IO.Path]::GetFullPath((Join-Path $taskPhasePath 'obj'))
        if (!$taskAbsolute.StartsWith($taskResultRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw "Outside results: $taskAbsolute" }
        if ([IO.Path]::GetFileName($taskAbsolute) -ne 'obj') { throw 'Invalid cache target' }
        if (!(Test-Path -LiteralPath $taskAbsolute)) { continue }
        $taskCursor = Get-Item -LiteralPath $taskAbsolute
        while ($taskCursor.FullName.Length -ge $taskResultRoot.Length) {
            if ($taskCursor.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse point: $($taskCursor.FullName)" }
            $taskCursor = $taskCursor.Parent
        }
        $taskFiles = @(Get-ChildItem -LiteralPath $taskAbsolute -Recurse -Force)
        if ($taskFiles | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }) { throw "Reparse point inside: $taskAbsolute" }
        $taskBytes = [long](($taskFiles | Where-Object { !$_.PSIsContainer } | Measure-Object -Property Length -Sum).Sum)
        $taskTargets += [PSCustomObject]@{ path=$taskAbsolute; bytes=$taskBytes }
    }
}
# All resolved paths and successful simulation results were checked above.
foreach ($taskTarget in $taskTargets) {
    Remove-Item -LiteralPath $taskTarget.path -Recurse -Force
    if (Test-Path -LiteralPath $taskTarget.path) { throw 'Incomplete deletion' }
}
$taskReport = [ordered]@{ date=(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'); root=$taskRoot; removed_directories=$taskTargets.Count; reclaimed_bytes=[long](($taskTargets | Measure-Object -Property bytes -Sum).Sum); scope='Completed LSU performance/validation obj caches only; RTL, firmware, logs, traces, result JSON, PDS databases and immutable archives preserved.'; removed=$taskTargets }
$taskReport | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskRoot 'simulation\cleanup_completed_lsu_result.json') -Encoding utf8
[PSCustomObject]@{ removed_directories=$taskTargets.Count; reclaimed_GiB=[Math]::Round($taskReport.reclaimed_bytes/1GB,3) } | ConvertTo-Json
