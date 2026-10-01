param(
    [Parameter(Mandatory = $true)]
    [int]$InputDevice,
    [Parameter(Mandatory = $true)]
    [int]$OutputDevice,
    [int]$PrimaryChannel = 0,
    [ValidateRange(0.0, 1.0)]
    [double]$WetMix = 0.60,
    [ValidateRange(1, 64)]
    [int]$Threads = 2,
    [ValidateRange(1, 8)]
    [int]$PlayoutExtraBlocks = 2,
    [ValidateRange(0.0, 86400.0)]
    [double]$DurationSeconds = 0,
    [ValidateRange(1024, 65535)]
    [int]$DashboardPort = 8765,
    [switch]$NoDashboard
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$live = Join-Path $projectRoot '.venv\Scripts\voxshield-live.exe'
$dashboard = Join-Path $projectRoot '.venv\Scripts\voxshield-dashboard.exe'
$checkpoint = Join-Path $projectRoot 'checkpoints_ulunas_v6_full\best.pt'
$onnx = Join-Path $projectRoot 'artifacts\voxshield-v6-full-stream.onnx'
$telemetry = Join-Path $projectRoot 'artifacts\v6-laptop-live-telemetry.json'
$session = Join-Path $projectRoot 'artifacts\v6-laptop-live-session.json'

foreach ($required in @($live, $dashboard, $checkpoint, $onnx)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing required laptop-demo file: $required"
    }
}

Write-Warning 'Use headphones. Speaker monitoring can create loud acoustic feedback.'
Write-Host 'Laptop-safe mono mode: UL-UNAS v6, no duplicated reference channel, voice-preserving 60% wet mix.'
Write-Host 'This is the correct demo mode until a synchronized, separately positioned reference microphone is available.'

$dashboardProcess = $null
try {
    if (-not $NoDashboard) {
        $requestedPort = $DashboardPort
        while ($DashboardPort -lt 65535) {
            $probe = [System.Net.Sockets.TcpListener]::new(
                [System.Net.IPAddress]::Loopback,
                $DashboardPort
            )
            try {
                $probe.Start()
                break
            }
            catch [System.Net.Sockets.SocketException] {
                $DashboardPort += 1
            }
            finally {
                $probe.Stop()
            }
        }
        if ($DashboardPort -ge 65535) {
            throw 'Could not find a free local port for the engineering dashboard.'
        }
        if ($DashboardPort -ne $requestedPort) {
            Write-Warning "Dashboard port $requestedPort is already in use; using $DashboardPort instead."
        }
        $dashboardProcess = Start-Process -FilePath $dashboard -ArgumentList @(
            '--telemetry-file', $telemetry,
            '--host', '127.0.0.1',
            '--port', "$DashboardPort"
        ) -PassThru -WindowStyle Hidden
        Write-Host "Engineering monitor: http://127.0.0.1:$DashboardPort/"
    }

    $liveArgs = @(
        '--checkpoint', $checkpoint,
        '--onnx', $onnx,
        '--input-device', "$InputDevice",
        '--output-device', "$OutputDevice",
        '--primary-channel', "$PrimaryChannel",
        '--threads', "$Threads",
        '--queue-blocks', '16',
        '--playout-extra-blocks', "$PlayoutExtraBlocks",
        '--wet-mix', "$WetMix",
        '--telemetry-file', $telemetry,
        '--session-report', $session
    )
    if ($DurationSeconds -gt 0) {
        $liveArgs += @('--duration-seconds', "$DurationSeconds")
    }
    & $live @liveArgs
    if ($LASTEXITCODE -ne 0) {
        throw "voxshield-live exited with code $LASTEXITCODE"
    }
}
finally {
    if ($null -ne $dashboardProcess -and -not $dashboardProcess.HasExited) {
        Stop-Process -Id $dashboardProcess.Id
    }
}
