#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"
checkpoint="checkpoints_deep_filter_v10/best.pt"
onnx="artifacts/voxshield-v10-deep-filter-final.onnx"
output_dir="artifacts/pi5-v10-verification"
mkdir -p "$output_dir"

for required in .venv/bin/voxshield-benchmark "$checkpoint" "$onnx"; do
  [[ -e "$required" ]] || { echo "Missing required file: $required" >&2; exit 1; }
done

bash scripts/pi/health-check.sh > "$output_dir/health-before.txt"
.venv/bin/voxshield-benchmark \
  --checkpoint "$checkpoint" --onnx "$onnx" --device cpu --threads 1 \
  --warmup 200 --frames 10000 --output "$output_dir/benchmark.json"
bash scripts/pi/health-check.sh > "$output_dir/health-after.txt"
sha256sum "$checkpoint" "$onnx" > "$output_dir/artifact-sha256.txt"

python3 - "$output_dir/benchmark.json" <<'PY'
import json
import pathlib
import sys

report = json.loads(pathlib.Path(sys.argv[1]).read_text())
checks = {
    "mean_real_time": bool(report.get("meets_realtime_mean")),
    "p99_below_frame_deadline": float(report["full_pipeline_p99_callback_ms"]) < float(report["frame_duration_ms"]),
    "zero_deadline_overruns": int(report.get("runtime_deadline_overruns", -1)) == 0,
    "zero_simulated_callback_drops": int(report.get("dropped_or_underflowed_audio_callbacks", -1)) == 0,
}
summary = {"passed": all(checks.values()), "checks": checks, "benchmark": report}
path = pathlib.Path(sys.argv[1]).with_name("acceptance.json")
path.write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
raise SystemExit(0 if summary["passed"] else 1)
PY

echo "Pi 5 verification evidence: $output_dir"

