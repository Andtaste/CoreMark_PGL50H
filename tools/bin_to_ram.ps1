param(
    [Parameter(Mandatory = $true)][string]$BinaryPath,
    [Parameter(Mandatory = $true)][string]$OutputPath
)

$ErrorActionPreference = 'Stop'
try {
    $programBytes = [System.IO.File]::ReadAllBytes(
        $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($BinaryPath)
    )
    if ($programBytes.Length -eq 0 -or $programBytes.Length -gt 65536) {
        throw 'BIN must contain 1..65536 bytes for the 64 KiB ram1.'
    }
    $memoryBytes = New-Object byte[] 65536
    [System.Array]::Copy($programBytes, $memoryBytes, $programBytes.Length)
    $hexLines = New-Object string[] 16384
    for ($wordIndex = 0; $wordIndex -lt 16384; $wordIndex++) {
        $offset = $wordIndex * 4
        $hexLines[$wordIndex] = '{0:X2}{1:X2}{2:X2}{3:X2}' -f `
            $memoryBytes[$offset + 3], $memoryBytes[$offset + 2], `
            $memoryBytes[$offset + 1], $memoryBytes[$offset]
    }
    $resolvedOutput = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)
    [System.IO.File]::WriteAllLines($resolvedOutput, $hexLines, [System.Text.Encoding]::ASCII)
    Write-Host "RAM_INIT_OK: $($programBytes.Length) BIN bytes, 16384 words -> $resolvedOutput"
    exit 0
} catch {
    [Console]::Error.WriteLine("RAM_INIT_FAILED: $($_.Exception.Message)")
    exit 1
}
