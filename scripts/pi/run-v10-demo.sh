#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: bash scripts/pi/run-v10-demo.sh INPUT_DEVICE OUTPUT_DEVICE [PRIMARY_CHANNEL] [REFERENCE_CHANNEL]" >&2
  exit 2
fi

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"
input_device="$1"
output_device="$2"
primary_channel="${3:-0}"
reference_channel="${4:-1}"
checkpoint="checkpoints_deep_filter_v10/best.pt"
onnx="artifacts/voxshield-v10-deep-filter-final.onnx"
telemetry="artifacts/pi5-v10-live-telemetry.json"
control="artifacts/pi5-v10-live-control.json"
events="artifacts/pi5-v10-live-events.jsonl"
session="artifacts/pi5-v10-live-session.json"

for required in .venv/bin/voxshield-live .venv/bin/voxshield-dashboard "$checkpoint" "$onnx"; do
  [[ -e "$required" ]] || { echo "Missing required file: $required" >&2; exit 1; }
done
[[ "$primary_channel" != "$reference_channel" ]] || { echo "Primary and reference channels must differ." >&2; exit 2; }

printf '%s' '{"wet_mix":0.82,"output_gain_db":0.0,"operator_bypass":false,"mute_output":false,"preset":"balanced"}' > "$control"
.venv/bin/voxshield-dashboard \
  --telemetry-file "$telemetry" --control-file "$control" --event-file "$events" \
  --host 0.0.0.0 --port 8765 &
dashboard_pid=$!
cleanup() { kill "$dashboard_pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "VoxShield Console: http://$(hostname -I | awk '{print $1}'):8765/"
echo "Use wired headphones. Keep the console on a trusted local network only."
.venv/bin/voxshield-live \
  --checkpoint "$checkpoint" --onnx "$onnx" \
  --input-device "$input_device" --output-device "$output_device" \
  --primary-channel "$primary_channel" --reference-channel "$reference_channel" \
  --threads 1 --queue-blocks 16 --playout-extra-blocks 2 --wet-mix 0.82 \
  --telemetry-file "$telemetry" --control-file "$control" --session-report "$session"

