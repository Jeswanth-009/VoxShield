param(
    [Parameter(Mandatory = $true)]
    [int]$InputDevice,
    [Parameter(Mandatory = $true)]
    [int]$OutputDevice,
    [int]$PrimaryChannel = 0,
    [int]$ReferenceChannel = 1,
    [ValidateRange(0.0, 1.0)]
    [double]$WetMix = 0.90,
    [ValidateRange(1, 64)]
    [int]$Threads = 1,
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
$checkpoint = Join-Path $projectRoot 'checkpoints_fusion_v7_stage2\best.pt'
$onnx = Join-Path $projectRoot 'artifacts\voxshield-v7-stage2-final.onnx'
$telemetry = Join-Path $projectRoot 'artifacts\v7-live-telemetry.json'
$session = Join-Path $projectRoot 'artifacts\v7-live-session.json'

foreach ($required in @($live, $checkpoint, $onnx)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing required live-demo file: $required"
    }
}
if ($PrimaryChannel -eq $ReferenceChannel) {
    throw 'PrimaryChannel and ReferenceChannel must be different.'
}

Write-Warning 'Use headphones. Playing microphone audio through laptop speakers can create loud acoustic feedback.'
Write-Host 'The laptop microphone-array channels are suitable for an engineering demo, not proof of a correctly positioned noise-reference microphone.'

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
        '--reference-channel', "$ReferenceChannel",
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
