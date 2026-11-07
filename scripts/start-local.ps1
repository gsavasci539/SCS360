param(
    [ValidateRange(1024, 65535)][int]$BackendPort = 8000,
    [ValidateRange(1024, 65535)][int]$FrontendPort = 5173
)

$ErrorActionPreference = 'Stop'
if ($BackendPort -eq $FrontendPort) { throw 'Backend and frontend ports must differ.' }
$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$backendFolder = Join-Path $workspace 'backend'
$frontendFolder = Join-Path $workspace 'frontend'
$python = Join-Path $backendFolder '.venv\Scripts\python.exe'
$vite = Join-Path $frontendFolder 'node_modules\vite\bin\vite.js'
if (!(Test-Path -LiteralPath $python) -or !(Test-Path -LiteralPath $vite)) {
    throw 'Install backend/.venv and frontend/node_modules before starting. See README.md.'
}
$node = (Get-Command node.exe -ErrorAction Stop).Source
$stateFolder = Join-Path $workspace '.codex-build\local'
New-Item -ItemType Directory -Path $stateFolder -Force | Out-Null
$stateFile = Join-Path $stateFolder 'processes.json'
$backendUrl = "http://127.0.0.1:$BackendPort"
$frontendUrl = "http://127.0.0.1:$FrontendPort"
$created = [System.Collections.Generic.List[System.Diagnostics.Process]]::new()
$owned = [System.Collections.Generic.List[object]]::new()
$previous = @()
if (Test-Path -LiteralPath $stateFile) {
    $state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
    if ($state.workspace -eq $workspace) { $previous = @($state.processes) }
}

function Wait-Endpoint([string]$Url, [int]$Seconds = 120) {
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    do {
        try { return Invoke-RestMethod -Uri $Url -TimeoutSec 20 } catch { Start-Sleep -Milliseconds 400 }
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Service did not become ready: $Url. See $stateFolder logs."
}

function Find-Listener([int]$Port) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) { return $listener.OwningProcess }
    return $null
}

function Remember-Process($Process, [string]$Service, [string]$Executable) {
    $owned.Add([ordered]@{ id = $Process.Id; service = $Service; started_ticks = $Process.StartTime.ToUniversalTime().Ticks.ToString(); executable = $Executable })
}

try {
    $backendListener = Find-Listener $BackendPort
    if (!$backendListener) {
        $process = Start-Process -FilePath $python -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$BackendPort") -WorkingDirectory $backendFolder -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $stateFolder 'backend.log') -RedirectStandardError (Join-Path $stateFolder 'backend-error.log')
        $created.Add($process)
        Remember-Process $process 'backend' $python
    }
    $null = Wait-Endpoint "$backendUrl/health"
    $schema = Wait-Endpoint "$backendUrl/api/openapi.json"
    if ($schema.info.title -ne 'SCS360 API') { throw "Port $BackendPort belongs to another application." }
    $null = Wait-Endpoint "$backendUrl/api/ready"

    $frontendListener = Find-Listener $FrontendPort
    if (!$frontendListener) {
        $oldProxy = $env:VITE_DEV_PROXY_TARGET
        $oldApiBase = $env:VITE_API_BASE_URL
        try {
            $env:VITE_DEV_PROXY_TARGET = $backendUrl
            $env:VITE_API_BASE_URL = '/api'
            $process = Start-Process -FilePath $node -ArgumentList @("`"$vite`"", '--host', '127.0.0.1', '--port', "$FrontendPort", '--strictPort') -WorkingDirectory $frontendFolder -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $stateFolder 'frontend.log') -RedirectStandardError (Join-Path $stateFolder 'frontend-error.log')
            $created.Add($process)
            Remember-Process $process 'frontend' $node
        } finally {
            $env:VITE_DEV_PROXY_TARGET = $oldProxy
            $env:VITE_API_BASE_URL = $oldApiBase
        }
    }
    $null = Wait-Endpoint "$frontendUrl/scs360-mark.svg"
    $proxied = Wait-Endpoint "$frontendUrl/api/openapi.json"
    if ($proxied.info.title -ne 'SCS360 API') { throw 'Frontend API proxy points to another application.' }
    foreach ($record in $previous) {
        $running = Get-Process -Id $record.id -ErrorAction SilentlyContinue
        if ($running -and $running.StartTime.ToUniversalTime().Ticks.ToString() -eq $record.started_ticks -and $running.Path -eq $record.executable -and !($owned | Where-Object { $_.id -eq $record.id })) {
            $owned.Add($record)
        }
    }
    [ordered]@{ workspace = $workspace; frontend = $frontendUrl; backend = $backendUrl; processes = @($owned.ToArray()) } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $stateFile -Encoding utf8
    Write-Output "SCS360: $frontendUrl"
    Write-Output "API: $backendUrl/api/docs"
    Write-Output "Logs: $stateFolder"
} catch {
    foreach ($process in $created) {
        $process.Refresh()
        if (!$process.HasExited) { Stop-Process -Id $process.Id -ErrorAction SilentlyContinue }
    }
    throw
}
