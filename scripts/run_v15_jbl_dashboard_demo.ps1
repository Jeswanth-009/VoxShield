param(
    [int]$PrimaryDevice = 1,
    [int]$ReferenceDevice = 2,
    [int]$OutputDevice = 5,
    [ValidateRange(0.0, 1.0)]
    [double]$WetMix = 0.82,
    [ValidateRange(1024, 65535)]
    [int]$DashboardPort = 8765,
    [ValidateRange(0.0, 1.0)]
    [double]$ControlledReferenceMix = 0.30,
    [switch]$EnableLms
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$dashboard = Join-Path $projectRoot '.venv\Scripts\voxshield-dashboard.exe'
$checkpoint = Join-Path $projectRoot 'release\v15\best.pt'
$onnx = Join-Path $projectRoot 'release\v15\voxshield-v15.onnx'
if (-not (Test-Path -LiteralPath $checkpoint)) {
    $checkpoint = Join-Path $projectRoot 'checkpoints_deep_filter_v15_hard_failure_repair\best.pt'
}
if (-not (Test-Path -LiteralPath $onnx)) {
    $onnx = Join-Path $projectRoot 'artifacts\voxshield-v15-hard-failure-repair-final.onnx'
}
$telemetry = Join-Path $projectRoot 'artifacts\v15-jbl-demo-telemetry.json'
$control = Join-Path $projectRoot 'artifacts\v15-jbl-demo-control.json'
$events = Join-Path $projectRoot 'artifacts\v15-jbl-demo-events.jsonl'
$session = Join-Path $projectRoot 'artifacts\v15-jbl-demo-session.json'

foreach ($required in @($python, $dashboard, $checkpoint, $onnx)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing required demo file: $required"
    }
}
New-Item -ItemType Directory -Path (Join-Path $projectRoot 'artifacts') -Force | Out-Null
if ($PrimaryDevice -eq $ReferenceDevice) {
    throw 'PrimaryDevice and ReferenceDevice must be different endpoints.'
}

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

Write-Host ''
Write-Host 'VoxShield v15 JBL demonstration' -ForegroundColor Cyan
Write-Host "  Voice microphone : device $PrimaryDevice"
Write-Host "  Environment mic  : device $ReferenceDevice"
Write-Host "  Headphone output : device $OutputDevice"
if ($ControlledReferenceMix -gt 0) {
    Write-Host "  Controlled mix   : JBL voice + $ControlledReferenceMix x laptop reference" -ForegroundColor Yellow
    Write-Host '  Dry/bypass will play the combined noisy test input. This is a disclosed demo mode.' -ForegroundColor Yellow
}
Write-Host 'During the first four seconds, remain silent and play the demonstration noise near the laptop.'
Write-Host ''

# A demonstration must start from a known state. Previous dashboard slider
# positions (especially a large negative output trim) must not leak into a run.
@{
    wet_mix = $WetMix
    effective_wet_mix = 0.0
    output_gain_db = 0.0
    operator_bypass = $false
    mute_output = $false
    preset = 'balanced'
    operating_mode = 'auto'
} | ConvertTo-Json | Set-Content -LiteralPath $control -Encoding UTF8

$dashboardProcess = Start-Process -FilePath $dashboard -ArgumentList @(
    '--telemetry-file', $telemetry,
    '--control-file', $control,
    '--event-file', $events,
    '--host', '127.0.0.1',
    '--port', "$DashboardPort",
    '--open-browser'
) -PassThru -WindowStyle Hidden

Write-Host "Dashboard: http://127.0.0.1:$DashboardPort/" -ForegroundColor Green

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
        '--queue-blocks', '16',
        '--playout-extra-blocks', '2',
        '--calibration-seconds', '4',
        '--controlled-reference-mix', "$ControlledReferenceMix",
        '--control-file', $control,
        '--telemetry-file', $telemetry,
        '--session-report', $session
    )
    if ($EnableLms) {
        $liveArgs += '--lms'
    }
    & $python @liveArgs
    if ($LASTEXITCODE -ne 0) {
        throw "VoxShield live demo exited with code $LASTEXITCODE"
    }
}
finally {
    if ($null -ne $dashboardProcess -and -not $dashboardProcess.HasExited) {
        Stop-Process -Id $dashboardProcess.Id
    }
}
