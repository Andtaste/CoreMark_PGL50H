$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskResults = [IO.Path]::GetFullPath((Join-Path $taskRoot 'simulation\results'))
$taskTargets = @()
foreach ($taskName in @('load_bp_dual_boundary_clock','load_bp_dual_boundary_side','load_bp_dual_boundary_pair','load_bp_dual_boundary_uart')) {
    $taskFolder = Get-Item -LiteralPath (Join-Path $taskResults $taskName)
    foreach ($taskCache in (Get-ChildItem -LiteralPath $taskFolder.FullName -Directory -Recurse -Filter obj)) {
        $taskAbsolute = [IO.Path]::GetFullPath($taskCache.FullName)
        if (!$taskAbsolute.StartsWith($taskResults + '\', [StringComparison]::OrdinalIgnoreCase)) { throw "Outside result workspace: $taskAbsolute" }
        if ([IO.Path]::GetFileName($taskAbsolute) -ne 'obj') { throw 'Invalid cache name' }
        $taskCursor = Get-Item -LiteralPath $taskAbsolute
        while ($taskCursor.FullName.Length -ge $taskResults.Length) {
            if ($taskCursor.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse point in cache path' }
            $taskCursor = $taskCursor.Parent
        }
        $taskEntries = @(Get-ChildItem -LiteralPath $taskAbsolute -Force -Recurse)
        if ($taskEntries | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }) { throw 'Reparse point inside cache' }
        $taskTargets += [PSCustomObject]@{path=$taskAbsolute;bytes=[long](($taskEntries | Where-Object { !$_.PSIsContainer } | Measure-Object Length -Sum).Sum)}
    }
}
# Run only after this round's simulator sessions finish. PDS does not use obj.
foreach ($taskTarget in $taskTargets) {
    Remove-Item -LiteralPath $taskTarget.path -Recurse -Force
    if (Test-Path -LiteralPath $taskTarget.path) { throw 'Incomplete cache deletion' }
}
$taskReport = [ordered]@{root=$taskRoot;date=(Get-Date -Format 'yyyy-MM-dd HH:mm:ss');removed_directories=$taskTargets.Count;reclaimed_bytes=[long](($taskTargets | Measure-Object bytes -Sum).Sum);scope='Timing80 round only; completed Verilator obj caches. All source, images, traces, logs, results and PDS outputs preserved.';removed=$taskTargets}
$taskReport | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskRoot 'simulation\cleanup_dual_timing80_result.json') -Encoding utf8
[PSCustomObject]@{removed_directories=$taskTargets.Count;reclaimed_GiB=[Math]::Round($taskReport.reclaimed_bytes/1GB,3)} | ConvertTo-Json
