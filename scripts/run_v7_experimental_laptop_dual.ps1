param(
    [int]$PrimaryDevice = 1,
    [int]$ReferenceDevice = 2,
    [int]$OutputDevice = 5,
    [ValidateRange(0.0, 1.0)]
    [double]$WetMix = 0.65,
    [ValidateRange(1024, 65535)]
    [int]$DashboardPort = 8765,
    [switch]$EnableLms
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$dashboard = Join-Path $projectRoot '.venv\Scripts\voxshield-dashboard.exe'
$checkpoint = Join-Path $projectRoot 'checkpoints_fusion_v7_stage2\best.pt'
$onnx = Join-Path $projectRoot 'artifacts\voxshield-v7-stage2-final.onnx'
$telemetry = Join-Path $projectRoot 'artifacts\v7-experimental-dual-telemetry.json'
$session = Join-Path $projectRoot 'artifacts\v7-experimental-dual-session.json'

foreach ($required in @($python, $dashboard, $checkpoint, $onnx)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing required demo file: $required"
    }
}
if ($PrimaryDevice -eq $ReferenceDevice) {
    throw 'PrimaryDevice and ReferenceDevice must be different endpoints.'
}

Write-Warning 'Experimental laptop demo: separate Windows endpoints are acoustically aligned but not hardware-clock synchronized.'
Write-Warning 'Use headphones. During the initial calibration, play gun/noise near the laptop microphone and remain silent.'

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
    throw 'Could not find a free local dashboard port.'
}
if ($DashboardPort -ne $requestedPort) {
    Write-Warning "Dashboard port $requestedPort is occupied; using $DashboardPort."
}

$dashboardProcess = Start-Process -FilePath $dashboard -ArgumentList @(
    '--telemetry-file', $telemetry,
    '--host', '127.0.0.1',
    '--port', "$DashboardPort"
) -PassThru -WindowStyle Hidden
Write-Host "Engineering monitor: http://127.0.0.1:$DashboardPort/"

try {
    $liveArgs = @(
        '-m', 'voxshield.live_dual_device',
        '--checkpoint', $checkpoint,
        '--onnx', $onnx,
        '--primary-device', "$PrimaryDevice",
        '--reference-device', "$ReferenceDevice",
        '--output-device', "$OutputDevice",
        '--primary-channel', '0',
        '--reference-channel', '0',
        '--wet-mix', "$WetMix",
        '--threads', '2',
        '--calibration-seconds', '4',
        '--telemetry-file', $telemetry,
        '--session-report', $session
    )
    if ($EnableLms) {
        $liveArgs += '--lms'
    }
    & $python @liveArgs
    if ($LASTEXITCODE -ne 0) {
        throw "experimental dual-device demo exited with code $LASTEXITCODE"
    }
}
finally {
    if ($null -ne $dashboardProcess -and -not $dashboardProcess.HasExited) {
        Stop-Process -Id $dashboardProcess.Id
    }
}
