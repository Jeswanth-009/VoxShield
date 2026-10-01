#!/usr/bin/env bash
set -euo pipefail

echo "VoxShield Pi health snapshot"
uname -a
vcgencmd measure_temp || true
vcgencmd get_throttled || true
echo "ALSA capture/playback devices"
arecord -l || true
aplay -l || true
echo "Service status"
systemctl --no-pager --full status voxshield-v4.service || true
echo "Recent audio/model faults"
journalctl -u voxshield-v4.service -n 100 --no-pager || true
