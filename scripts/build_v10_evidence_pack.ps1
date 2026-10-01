param(
    [string]$OutputRoot = "",
    [ValidateRange(0,20)][int]$AudioSamplesPerSuite = 5
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $OutputRoot = Join-Path $projectRoot "artifacts\release-evidence-v10-$stamp"
}
$OutputRoot = [System.IO.Path]::GetFullPath($OutputRoot)
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null

$required = [ordered]@{
    'model/best.pt' = 'checkpoints_deep_filter_v10/best.pt'
    'model/voxshield-v10-deep-filter-final.onnx' = 'artifacts/voxshield-v10-deep-filter-final.onnx'
    'model/onnx-validation.json' = 'artifacts/voxshield-v10-deep-filter-final.validation.json'
    'evaluation/broad-50.json' = 'artifacts/v10-final-broad-50.json'
    'evaluation/broad-50-dnsmos.json' = 'artifacts/v10-final-broad-50-dnsmos.json'
    'evaluation/military-50.json' = 'artifacts/v10-final-military-50.json'
    'benchmark/laptop-cpu-onnx.json' = 'artifacts/v10-laptop-benchmark.json'
    'verification/pytest-junit.xml' = 'artifacts/v10-test-report.xml'
    'data/data-audit.json' = 'artifacts/data-audit-v5.json'
    'data/frozen-manifests.json' = 'artifacts/frozen-manifests-v4.json'
    'documentation/project-status.md' = 'docs/project-completion-status.md'
    'documentation/master-document.docx' = 'docs/VoxShield_SIH_26052_Master_Document.docx'
    'documentation/laptop-demo.md' = 'docs/laptop-demo.md'
    'documentation/deployment-pi5.md' = 'docs/deployment-pi5.md'
    'documentation/hardware-inventory-template.csv' = 'docs/hardware-inventory-template.csv'
    'source/README.md' = 'README.md'
    'source/configs/deep_filter_v10.yaml' = 'configs/deep_filter_v10.yaml'
    'source/voxshield/df_model.py' = 'src/voxshield/df_model.py'
    'source/voxshield/train.py' = 'src/voxshield/train.py'
    'source/voxshield/evaluate.py' = 'src/voxshield/evaluate.py'
    'source/voxshield/export_onnx.py' = 'src/voxshield/export_onnx.py'
    'source/voxshield/runtime.py' = 'src/voxshield/runtime.py'
    'source/voxshield/live.py' = 'src/voxshield/live.py'
    'source/voxshield/telemetry.py' = 'src/voxshield/telemetry.py'
    'source/voxshield/dashboard.py' = 'src/voxshield/dashboard.py'
    'source/voxshield/dashboard_ui.py' = 'src/voxshield/dashboard_ui.py'
    'source/scripts/run_v10_laptop_demo.ps1' = 'scripts/run_v10_laptop_demo.ps1'
    'source/scripts/build_v10_evidence_pack.ps1' = 'scripts/build_v10_evidence_pack.ps1'
    'source/scripts/pi/run-v10-demo.sh' = 'scripts/pi/run-v10-demo.sh'
    'source/scripts/pi/verify-v10.sh' = 'scripts/pi/verify-v10.sh'
}

foreach ($entry in $required.GetEnumerator()) {
    $source = Join-Path $projectRoot $entry.Value
    if (-not (Test-Path -LiteralPath $source)) { throw "Missing required evidence: $source" }
    $destination = Join-Path $OutputRoot $entry.Key
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

foreach ($suite in @('broad','military')) {
    $sourceDir = Join-Path $projectRoot "artifacts\v10-final-$suite-audio"
    if (Test-Path -LiteralPath $sourceDir) {
        $destinationDir = Join-Path $OutputRoot "listening\$suite-enhanced"
        New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
        Get-ChildItem -LiteralPath $sourceDir -File -Filter '*.wav' |
            Sort-Object Name | Select-Object -First $AudioSamplesPerSuite |
            Copy-Item -Destination $destinationDir -Force
    }
}

$optional = [ordered]@{
    'live/latest-telemetry.json' = 'artifacts/v10-live-telemetry.json'
    'live/latest-control.json' = 'artifacts/v10-live-control.json'
    'live/latest-events.jsonl' = 'artifacts/v10-live-events.jsonl'
    'live/latest-session.json' = 'artifacts/v10-live-session.json'
}
foreach ($entry in $optional.GetEnumerator()) {
    $source = Join-Path $projectRoot $entry.Value
    if (Test-Path -LiteralPath $source) {
        $destination = Join-Path $OutputRoot $entry.Key
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }
}

$summary = @"
# VoxShield v10 evidence package

Generated: $((Get-Date).ToUniversalTime().ToString('u')) UTC

This package freezes the selected v10 checkpoint, FP32 ONNX model, ONNX parity validation,
broad and military evaluations, DNSMOS supplement, data audits, laptop CPU benchmark,
sample enhanced audio, project status and master document. Every included evidence file is covered
by `SHA256-MANIFEST.json`; the manifest itself is the only intentional exception.

Important limitations: military reliability is not yet a full pass across every frozen sample;
the laptop benchmark does not measure microphone/headphone I/O latency; Raspberry Pi 5 results
must be measured on the Pi; and a laptop microphone array is not a substitute for a correctly
positioned synchronized reference microphone.
"@
$summary | Set-Content -LiteralPath (Join-Path $OutputRoot 'README.md') -Encoding utf8

$hashes = Get-ChildItem -LiteralPath $OutputRoot -File -Recurse |
    Where-Object { $_.Name -ne 'SHA256-MANIFEST.json' } | ForEach-Object {
        $relative = [System.IO.Path]::GetRelativePath($OutputRoot, $_.FullName).Replace('\','/')
        $hash = Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256
        [ordered]@{ path = $relative; bytes = $_.Length; sha256 = $hash.Hash.ToLowerInvariant() }
    }
$manifest = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString('o')
    baseline = 'v10 deep-filter dual'
    team = 'Team@'
    problem_statement_id = '26052'
    note = 'Laptop timings are software processing measurements, not physical end-to-end audio latency. Raspberry Pi 5 remains to be measured on-device.'
    files = @($hashes)
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $OutputRoot 'SHA256-MANIFEST.json') -Encoding utf8

Write-Host "Evidence package created: $OutputRoot"
Write-Host "Files hashed: $($hashes.Count)"
