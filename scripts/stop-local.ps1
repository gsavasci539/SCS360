$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$stateFile = Join-Path $workspace '.codex-build\local\processes.json'
if (!(Test-Path -LiteralPath $stateFile)) { Write-Output 'No managed local servers were recorded.'; return }
$state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
if ($state.workspace -ne $workspace) { throw 'The process file belongs to another workspace.' }
foreach ($record in @($state.processes)) {
    $process = Get-Process -Id $record.id -ErrorAction SilentlyContinue
    if (!$process) { continue }
    if ($process.StartTime.ToUniversalTime().Ticks.ToString() -ne $record.started_ticks -or $process.Path -ne $record.executable) {
        Write-Output "Skipped reused or unrelated process ID: $($record.id)"
        continue
    }
    Stop-Process -Id $process.Id
    Write-Output "Stopped $($record.service)."
}
