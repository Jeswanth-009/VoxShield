param(
    [Parameter(Mandatory = $true)][int]$InputDevice,
    [Parameter(Mandatory = $true)][int]$OutputDevice,
    [int]$PrimaryChannel = 0,
    [int]$ReferenceChannel = 1,
    [ValidateRange(0.0,1.0)][double]$WetMix = 0.82,
    [ValidateRange(1,16)][int]$Threads = 1,
    [ValidateRange(1,8)][int]$PlayoutExtraBlocks = 2,
    [ValidateRange(0.0,86400.0)][double]$DurationSeconds = 0,
    [ValidateRange(1024,65535)][int]$DashboardPort = 8765,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$live = Join-Path $projectRoot '.venv\Scripts\voxshield-live.exe'
$dashboard = Join-Path $projectRoot '.venv\Scripts\voxshield-dashboard.exe'
$checkpoint = Join-Path $projectRoot 'checkpoints_deep_filter_v10\best.pt'
$onnx = Join-Path $projectRoot 'artifacts\voxshield-v10-deep-filter-final.onnx'
$telemetry = Join-Path $projectRoot 'artifacts\v10-live-telemetry.json'
$control = Join-Path $projectRoot 'artifacts\v10-live-control.json'
$events = Join-Path $projectRoot 'artifacts\v10-live-events.jsonl'
$session = Join-Path $projectRoot 'artifacts\v10-live-session.json'

foreach ($required in @($live,$dashboard,$checkpoint,$onnx)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Missing demo file: $required" }
}
if ($PrimaryChannel -eq $ReferenceChannel) { throw 'Primary and reference channels must differ.' }

@{wet_mix=$WetMix;output_gain_db=0.0;operator_bypass=$false;mute_output=$false;preset='balanced'} |
    ConvertTo-Json -Compress | Set-Content -LiteralPath $control -Encoding utf8

Write-Warning 'Use headphones. Loudspeaker monitoring can cause acoustic feedback.'
Write-Warning 'Laptop array channels are a demonstration substitute, not proof of a correctly positioned reference microphone.'
$dashboardProcess = $null
try {
    while ($DashboardPort -lt 65535) {
        $probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,$DashboardPort)
        try { $probe.Start(); break } catch [System.Net.Sockets.SocketException] { $DashboardPort++ } finally { $probe.Stop() }
    }
    $dashboardArgs = @('--telemetry-file',$telemetry,'--control-file',$control,'--event-file',$events,'--host','127.0.0.1','--port',"$DashboardPort")
    if (-not $NoBrowser) { $dashboardArgs += '--open-browser' }
    $dashboardProcess = Start-Process -FilePath $dashboard -ArgumentList $dashboardArgs -PassThru -WindowStyle Hidden
    Write-Host "VoxShield Console: http://127.0.0.1:$DashboardPort/"
    $liveArgs = @('--checkpoint',$checkpoint,'--onnx',$onnx,'--input-device',"$InputDevice",'--output-device',"$OutputDevice",'--primary-channel',"$PrimaryChannel",'--reference-channel',"$ReferenceChannel",'--threads',"$Threads",'--queue-blocks','16','--playout-extra-blocks',"$PlayoutExtraBlocks",'--wet-mix',"$WetMix",'--telemetry-file',$telemetry,'--control-file',$control,'--session-report',$session)
    if ($DurationSeconds -gt 0) { $liveArgs += @('--duration-seconds',"$DurationSeconds") }
    & $live @liveArgs
    if ($LASTEXITCODE -ne 0) { throw "voxshield-live exited with code $LASTEXITCODE" }
}
finally {
    if ($null -ne $dashboardProcess -and -not $dashboardProcess.HasExited) { Stop-Process -Id $dashboardProcess.Id }
}
